#!/usr/bin/env bash
# Bring up the whole CivicPulse stack on a local k3d cluster, reproducibly.
#
#   scripts/k8s-up.sh                 # create if missing, then deploy + verify
#   scripts/k8s-up.sh --recreate      # throw the cluster away and rebuild it
#   CP_HOST_PORT=80 scripts/k8s-up.sh # use another host port (80 is often busy)
#   scripts/k8s-up.sh --no-vpa        # skip the VPA recommender
#
# Why a script: the manual path had three non-obvious traps, all handled below.
#   1. k3d's importer silently skips some OCI-index images -> `ctr` fallback.
#   2. The VPA CRD must be applied in its own stream, before the overlays.
#   3. The registry cannot be relied on for every image -> local import.
#
# The backend image is the stub until backend/ lands; the script picks whichever
# Dockerfile exists, exactly like CI does.
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER=${CLUSTER:-civicpulse}
HOST_PORT=${CP_HOST_PORT:-8080}
RECREATE=0
WITH_VPA=1
IMAGE_TAG=dev
REG=ghcr.io/alihaiderbajwa

for arg in "$@"; do
  case "$arg" in
    --recreate) RECREATE=1 ;;
    --no-vpa) WITH_VPA=0 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

for bin in k3d kubectl docker; do
  command -v "$bin" >/dev/null || die "$bin is required but not installed"
done

# ---------------------------------------------------------------- cluster ----
if [ "$RECREATE" = 1 ] && k3d cluster list -o json 2>/dev/null | grep -q "\"$CLUSTER\""; then
  say "Deleting existing cluster $CLUSTER"
  k3d cluster delete "$CLUSTER"
fi

if k3d cluster list -o json 2>/dev/null | grep -q "\"$CLUSTER\""; then
  say "Reusing existing cluster $CLUSTER (delete it with --recreate)"
else
  say "Creating k3d cluster $CLUSTER (host :$HOST_PORT -> Traefik :80)"
  if ss -ltn 2>/dev/null | grep -q ":$HOST_PORT "; then
    die "host port $HOST_PORT is already in use. Override it: CP_HOST_PORT=<free> $0"
  fi
  k3d cluster create "$CLUSTER" -p "$HOST_PORT:80@loadbalancer" --wait 120s
fi
kubectl config use-context "k3d-$CLUSTER" >/dev/null

NODE="k3d-${CLUSTER}-server-0"

# ----------------------------------------------------------------- images ----
say "Building application images tagged :$IMAGE_TAG"
docker build -q -t "$REG/civicpulse-backend:$IMAGE_TAG" \
  "${BACKEND_CONTEXT:-tools/stub-backend}" >/dev/null
docker build -q -t "$REG/civicpulse-frontend:$IMAGE_TAG" frontend >/dev/null

IMAGES=(
  postgres:16-alpine
  redis:7-alpine
  "$REG/civicpulse-backend:$IMAGE_TAG"
  "$REG/civicpulse-frontend:$IMAGE_TAG"
)
[ "$WITH_VPA" = 1 ] && IMAGES+=(registry.k8s.io/autoscaling/vpa-recommender:1.7.1)

say "Pulling and importing ${#IMAGES[@]} images into the node"
# containerd rewrites names to fully-qualified form (postgres:16-alpine becomes
# docker.io/library/postgres:16-alpine), so match on a path boundary suffix.
in_node() { docker exec "$NODE" ctr -n k8s.io images ls -q | grep -qE "(^|/)${1}$"; }

for image in "${IMAGES[@]}"; do
  docker image inspect "$image" >/dev/null 2>&1 || docker pull -q "$image" >/dev/null
  k3d image import "$image" -c "$CLUSTER" >/dev/null 2>&1 || true
  if in_node "$image"; then
    echo "    ok (k3d importer): $image"
  else
    echo "    k3d importer skipped it, streaming via ctr: $image"
    docker save "$image" | docker exec -i "$NODE" ctr -n k8s.io images import -
    in_node "$image" || die "failed to import $image"
  fi
done

# ------------------------------------------------------------------ CRDs -----
# kubectl cannot map a custom resource in the same stream that installs its CRD,
# so the VPA CRD always goes in first, on its own.
say "Installing CRDs, then the VPA recommender"
kubectl apply -k k8s/crds
kubectl wait --for=condition=Established --timeout=60s \
  crd/verticalpodautoscalers.autoscaling.k8s.io
if [ "$WITH_VPA" = 1 ]; then
  kubectl apply -k k8s/vpa
  kubectl -n kube-system rollout status deploy/vpa-recommender --timeout=180s
else
  echo "    (--no-vpa: recommender skipped)"
fi

# ---------------------------------------------------------------- deploy -----
say "Deploying k8s/overlays/dev at tag :$IMAGE_TAG"
sed -i -E "s|newTag: .*|newTag: ${IMAGE_TAG}|" k8s/overlays/dev/kustomization.yaml
kubectl kustomize k8s/overlays/dev | kubectl apply -f -
# The committed Secret holds placeholders on purpose; replace it in place so the
# live values never have to live in git.
kubectl create secret generic civicpulse-secrets -n civicpulse \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-local-dev-password}" \
  --from-literal="DATABASE_URL=postgresql+psycopg://civicpulse:${POSTGRES_PASSWORD:-local-dev-password}@database:5432/civicpulse" \
  --from-literal="LLM_API_KEY=${LLM_API_KEY:-}" \
  --dry-run=client -o yaml | kubectl replace -f -

say "Waiting for rollouts"
for w in deploy/backend deploy/frontend sts/postgres deploy/redis; do
  kubectl -n civicpulse rollout status "$w" --timeout=180s
done

# ------------------------------------------------------------------ smoke ----
say "Smoke-testing the Ingress on http://localhost:$HOST_PORT"
H="Host: civicpulse.localhost"
ok=0
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "$H" "http://localhost:$HOST_PORT/" || true)
  [ "$code" = "200" ] && { ok=1; break; }
  sleep 5
done
[ "$ok" = 1 ] || die "frontend never returned 200 through the Ingress"

code=$(curl -s -o /tmp/k8s-up-stats.json -w '%{http_code}' -H "$H" "http://localhost:$HOST_PORT/api/stats")
[ "$code" = "200" ] || die "GET /api/stats returned $code"
code=$(curl -s -o /tmp/k8s-up-c.json -w '%{http_code}' -X POST -H "$H" \
  -H 'content-type: application/json' \
  -d '{"text":"k8s-up.sh bring-up verification","location":"Local Test St"}' \
  "http://localhost:$HOST_PORT/api/complaints")
[ "$code" = "201" ] || die "POST /api/complaints returned $code"
echo "    GET /            200"
echo "    GET /api/stats   200"
# jq is not guaranteed locally (it is on the CI runner); stay portable.
triaged=$(grep -o '"triaged_by"[[:space:]]*:[[:space:]]*"[^"]*"' /tmp/k8s-up-c.json | head -1 | cut -d'"' -f4)
echo "    POST /api/complaints 201  -> triaged_by=${triaged:-unknown}"

say "Cluster state"
kubectl -n civicpulse get deploy,sts,svc,ingress,hpa,pdb
if [ "$WITH_VPA" = 1 ]; then
  echo
  echo "VPA recommendation (recommender observes, it never changes limits itself):"
  rec=""
  for _ in $(seq 1 12); do
    # the object is named backend-vpa, so never hardcode the name
    rec=$(kubectl -n civicpulse get vpa \
            -o jsonpath='{range .items[*]}{.metadata.name}: {.status.recommendation.containerRecommendations[*].target}{"\n"}{end}' 2>/dev/null || true)
    [ -n "$rec" ] && break
    sleep 5
  done
  echo "${rec:-    none yet (re-check: kubectl -n civicpulse get vpa -o yaml)}"
fi

cat <<EOF

CivicPulse is up.
  frontend   http://localhost:$HOST_PORT/          (send Host: civicpulse.localhost)
  api        http://localhost:$HOST_PORT/api/stats
  dashboard  kubectl -n civicpulse get all
  logs       kubectl -n civicpulse logs deploy/backend -f
  tear down  k3d cluster delete $CLUSTER
EOF
