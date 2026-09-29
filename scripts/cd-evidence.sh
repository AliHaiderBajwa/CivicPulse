#!/usr/bin/env bash
# Capture CD evidence from a completed GitHub Actions run into docs/evidence/.
#   usage: scripts/cd-evidence.sh <run-id> <output-file> [commit-sha]
# Log lines look like: <job>\t<step>\t<ts> <message>  -- drop the first two
# tab-separated fields and the timestamp, keep the message verbatim.
set -euo pipefail
RUN=${1:?run id required}
OUT=${2:?output file required}
COMMIT=${3:-$(git rev-parse HEAD)}
L=$(mktemp)
gh run view "$RUN" --log > "$L" 2>/dev/null
# Strip ANSI colour, the job/step tab fields, and the ISO timestamp prefix.
clean() {
  sed -E 's/\x1b\[[0-9;]*m//g; s/^\xef\xbb\xbf//' "$L" \
    | sed -E 's/^[^\t]*\t[^\t]*\t//' \
    | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z //'
}

{
  echo "CD evidence — ephemeral cluster deploy by commit SHA (rubric I4/I5/I6)"
  echo "run: https://github.com/AliHaiderBajwa/CivicPulse/actions/runs/$RUN"
  echo "commit: $COMMIT  (branch dev)"
  echo "captured: $(date -u +%Y-%m-%dT%H:%M:%SZ)  by: scripts/cd-evidence.sh (log verbatim)"
  echo
  echo "== job chain (build -> publish -> deploy-k8s, each gated by needs:) =="
  gh run view "$RUN" --json jobs --jq '.jobs[] | "  \(.name): \(.conclusion)"'
  echo
  echo "== I4: images published to GHCR tagged by commit SHA (never :latest) =="
  clean | grep -E "published: ghcr" | sed 's/^/  /'
  echo
  echo "== I4/I5: deploy-by-SHA rewrite actually applied to the overlay =="
  clean | grep -E "image: ghcr" | sort -u | sed 's/^/  /'
  echo
  echo "== VPA CRD installed in a separate stream before the overlay (fresh-cluster fix) =="
  clean | { grep -E "customresourcedefinition|condition Established|condition met" || true; } | head -5 | sed 's/^/  /'
  echo
  echo "== I5: rollout status waited for every workload =="
  clean | grep -E "successfully rolled out" | sed 's/^/  /'
  echo
  echo "== I5: Ingress smoke (GET /, GET /api/stats, POST /api/complaints) =="
  clean | grep -E "^(POST /api/complaints ->|ingress smoke OK)" | sed 's/^/  /'
  echo
  echo "== I6: secret plumbing — key names only, values never printed =="
  clean | grep -E "^secret key:" | sed 's/^/  /'
  echo "  LLM_API_KEY resolved from GitHub Secrets (masked as *** in the run log)"
  echo "  repository secrets (gh secret list):"
  gh secret list | sed 's/^/    /'
  echo
  echo "== I6: least-privilege permissions, nothing granted at workflow level =="
  python3 - <<'PY'
import yaml
d = yaml.safe_load(open('.github/workflows/cd.yml'))
print('  top-level permissions:', d.get('permissions'))
for n, j in d['jobs'].items():
    print(f"  {n}: {j['permissions']}  needs={j.get('needs')}")
PY
  echo
  echo "== I5: final cluster state (ephemeral kind) =="
  # the step name itself is stripped by clean(), so anchor on its command
  clean | awk '/kubectl -n civicpulse get deploy,sts,svc,ingress,hpa,pdb/,0' \
    | { grep -vE '##\[group\]|##\[endgroup\]|^$' || true; } | sed '/Post job cleanup/q'
} > "$OUT"
rm -f "$L"

# A capture that silently matched nothing must not look like a pass.
for needle in "published: ghcr" "successfully rolled out" "ingress smoke OK" "secret key:"; do
  grep -q "$needle" "$OUT" || { echo "ERROR: '$needle' absent from $OUT -- run id or log changed?" >&2; exit 1; }
done
echo "wrote $OUT ($(wc -l < "$OUT") lines, all required facts present)"
