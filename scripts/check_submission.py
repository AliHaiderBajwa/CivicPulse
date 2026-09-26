#!/usr/bin/env python3
"""CivicPulse submission gate.

Scans the repository for every automatic deduction listed in
docs/ASSIGNMENT-BRIEF.md section 5. Exit code 0 = clean, 1 = at least one
deduction would fire. Stdlib only; needs git on PATH.

    python3 scripts/check_submission.py
"""
from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[tuple[str, list[str]]] = []
PASSES: list[str] = []

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GitHub PAT (ghp_)", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub fine-grained PAT", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Groq-style key (gsk_)", re.compile(r"\bgsk_[A-Za-z0-9]{20,}")),
    ("OpenAI-style key (sk-)", re.compile(r"\bsk-[A-Za-z0-9_\-]{32,}\b")),
]
PLACEHOLDER = re.compile(r"change[-_]?me|placeholder|example|your[-_]|xxx|\.\.\.|set this|<.*>", re.IGNORECASE)


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False,
    )
    return out.stdout.strip()


def tracked() -> list[str]:
    return [line for line in git("ls-files").splitlines() if line]


def record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append((name, problems))
    else:
        PASSES.append(name)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def service_block(text: str, service: str) -> str:
    """Return the indented block of a top-level compose service."""
    lines = text.splitlines()
    start = re.compile(rf"^  {re.escape(service)}:\s*$")
    for i, line in enumerate(lines):
        if start.match(line):
            block = [line]
            for nxt in lines[i + 1 :]:
                if re.match(r"^  \S", nxt) and not nxt.startswith("    "):
                    break
                block.append(nxt)
            return "\n".join(block)
    return ""


def yaml_docs(path: str) -> list[str]:
    return [d for d in read(path).split("\n---\n") if d.strip()]


# ---------------------------------------------------------------- 1. .env history
def check_env_history() -> None:
    problems: list[str] = []
    added = git("log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:", "--", ".env")
    for line in added.splitlines():
        if line.strip() == ".env":
            problems.append(".env was added to git history at some point")
    for f in tracked():
        if f.endswith(".env") and not f.endswith(".env.example"):
            problems.append(f"tracked env file: {f}")
    record(".env never committed (deduction -20)", problems)


# ------------------------------------------------------- 2. keys in tracked files
def check_secrets_tracked() -> None:
    problems: list[str] = []
    for f in tracked():
        if f == "scripts/check_submission.py":
            continue  # this file contains the patterns themselves
        try:
            text = (ROOT / f).read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue  # binary
        for label, pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f}:{line_no} {label}")
    record("no key material in tracked files (deduction -20/-15)", problems)


# -------------------------------------------------------- 3. secrets in k8s yamls
def check_k8s_secrets() -> None:
    problems: list[str] = []
    for path in sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "k8s").rglob("*.yaml")):
        in_data = False
        for lineno, line in enumerate(read(path).splitlines(), 1):
            if re.match(r"^(data|stringData):", line.strip()) and not line.startswith(" "):
                in_data = line.startswith("data:")
                continue
            if in_data:
                if line and not line[0].isspace():
                    in_data = False
                    continue
                m = re.match(r"^\s+([A-Za-z0-9_.-]+):\s*(\S.*)$", line)
                if not m:
                    continue
                key, value = m.group(1), m.group(2).strip().strip('"').strip("'")
                if PLACEHOLDER.search(value):
                    continue
                decoded = value
                if re.fullmatch(r"[A-Za-z0-9+/=]+", value) and len(value) >= 8:
                    try:
                        decoded = base64.b64decode(value, validate=True).decode("utf-8", errors="replace")
                    except ValueError:  # binascii.Error subclasses ValueError: not valid base64
                        decoded = value  # inspect the literal text instead
                for label, pat in SECRET_PATTERNS:
                    if pat.search(decoded) or (key.upper().endswith(("KEY", "TOKEN")) and pat.search(decoded)):
                        problems.append(f"{path}:{lineno} decoded {label} in {key}")
                    elif re.search(r"PASSWORD|SECRET", key.upper(), re.IGNORECASE) and not PLACEHOLDER.search(decoded):
                        problems.append(f"{path}:{lineno} non-placeholder value in {key}")
    record("k8s manifests carry placeholders only (deduction -15)", problems)


# --------------------------------------------------------------- 4. pinned images
def check_pinned_images() -> None:
    problems: list[str] = []
    files = [
        str(p.relative_to(ROOT)).replace("\\", "/")
        for pat in ("compose*.yaml",)
        for p in ROOT.glob(pat)
    ] + [
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in (ROOT / "k8s").rglob("*.yaml")
    ] + [
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in (ROOT / ".github" / "workflows").glob("*.y*ml")
    ]
    for f in files:
        for lineno, line in enumerate(read(f).splitlines(), 1):
            m = re.search(r"image:\s*[\"']?([^\s\"'#]+)", line)
            if not m:
                continue
            image = m.group(1)
            if "image:" in line and image.endswith(":latest"):
                problems.append(f"{f}:{lineno} {image} uses :latest")
                continue
            if "${" in image:
                if re.search(r":latest", image):
                    problems.append(f"{f}:{lineno} {image} can resolve to :latest")
                continue  # parameterised tag (must be a SHA by deploy time; see check 9)
            tail = image.rsplit("/", 1)[-1]
            if ":" not in tail or tail.endswith(":"):
                problems.append(f"{f}:{lineno} {image} has no explicit tag")
    record("every container image pinned (deduction -8)", problems)


# --------------------------------------------------- 5. localhost service-to-service
def check_localhost_s2s() -> None:
    problems: list[str] = []
    files = [str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.glob("compose*.yaml")]
    files += [".env.example"]
    files += [str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "k8s").rglob("*.yaml")]
    # A service-to-service call reaches another container by URL/host:port.
    # Ingress hostnames like `civicpulse.localhost` are browser-side names, and
    # health probes run inside the same container - neither is a violation.
    s2s = re.compile(r"://localhost|://127\.0\.0\.1|@localhost[:/]|@127\.0\.0\.1[:/]|(?<![\w.])localhost:\d+|(?<![\w.])127\.0\.0\.1:\d+")
    for f in files:
        for lineno, line in enumerate(read(f).splitlines(), 1):
            if not s2s.search(line):
                continue
            if re.search(r"\btest:|\blivenessProbe\b|\breadinessProbe\b|\bstartupProbe\b", line):
                continue  # probe runs inside the same container / host-side port map
            problems.append(f"{f}:{lineno} {line.strip()[:110]}")
    record("no localhost in service-to-service config (deduction -8)", problems)


# ----------------------------------------------------- 6. frontend cannot reach DB
def check_frontend_db() -> None:
    problems: list[str] = []
    for f in ("compose.yaml", "compose.prod.yaml"):
        block = service_block(read(f), "frontend")
        if not block:
            problems.append(f"{f}: frontend service block not found")
            continue
        for pat in (r"DATABASE", r"POSTGRES", r"\b5432\b", r"pgdata"):
            if re.search(pat, block):
                problems.append(f"{f}: frontend block references {pat}")
    record("frontend has no path to the database (deduction -8)", problems)


# ------------------------------------------------- 7. DB/cache ports never published
def check_db_cache_ports() -> None:
    problems: list[str] = []
    prod = read("compose.prod.yaml")
    for svc in ("database", "cache"):
        block = service_block(prod, svc)
        if not block:
            problems.append(f"compose.prod.yaml: {svc} service block not found")
        elif re.search(r"^\s+ports:", block, re.MULTILINE):
            problems.append(f"compose.prod.yaml: {svc} publishes a host port")
    for doc in yaml_docs("k8s/base/services.yaml"):
        name = re.search(r"metadata:\s*\n\s+name:\s*(\S+)", doc)
        if not name:
            continue
        svc_name = name.group(1)
        if svc_name not in ("database", "cache"):
            continue
        typ = re.search(r"^\s+type:\s*(\S+)", doc, re.MULTILINE)
        if typ and typ.group(1) not in ("ClusterIP",):
            problems.append(f"k8s Service/{svc_name} type={typ.group(1)} (must be ClusterIP)")
    record("no published DB/cache port or NodePort/LB (deduction -8)", problems)


# ------------------------------------------------------- 8. publish/deploy gated
def check_gated_jobs() -> None:
    problems: list[str] = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = read(f".github/workflows/{wf.name}")
        m = re.search(r"^jobs:\s*$", text, re.MULTILINE)
        if not m:
            continue
        body = text[m.end() :]
        jobs = re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", body, re.MULTILINE)
        for job in jobs:
            if not re.search(r"publish|deploy|release", job, re.IGNORECASE):
                continue
            if re.search(r"^  verify", job):  # name-only matches like release-verify are fine below
                pass
            block_m = re.search(rf"^  {re.escape(job)}:\s*$", body, re.MULTILINE)
            if not block_m:
                continue
            block = body[block_m.end() :]
            nxt = re.search(r"^  [A-Za-z0-9_-]+:\s*$", block, re.MULTILINE)
            if nxt:
                block = block[: nxt.start()]
            if not re.search(r"^\s+needs:", block, re.MULTILINE):
                problems.append(f"{wf.name}: job '{job}' has no needs: gate")
    record("every publish/deploy job gated by needs: (deduction -8)", problems)


# ------------------------------------------------------- 9. never deploy :latest
def check_no_latest_deploy() -> None:
    problems: list[str] = []
    # Field-based scan: what the DEPLOY path renders (k8s manifests, prod
    # compose, kustomize tags) must never say :latest. GHCR publishing also
    # carries a `latest` convenience alias because the brief asks for it - that
    # is publish, not deploy, and deploy-k8s rewrites every tag to the SHA.
    image_fields = [
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in (ROOT / "k8s").rglob("*.yaml")
    ] + ["compose.prod.yaml"]
    for f in image_fields:
        for lineno, line in enumerate(read(f).splitlines(), 1):
            m = re.search(r"^\s*(?:image|newTag):\s*[\"']?([^\s\"'#]+)", line)
            if m and re.search(r":latest$", m.group(1)):
                problems.append(f"{f}:{lineno} {line.strip()[:110]}")
    # An IMAGE_TAG of `latest` would sail straight into compose.prod.yaml.
    for f in tracked():
        if not f.endswith((".yaml", ".yml", ".example", ".env")):
            continue
        for lineno, line in enumerate(read(f).splitlines(), 1):
            if re.match(r"^\s*IMAGE_TAG=latest\s*(#.*)?$", line):
                problems.append(f"{f}:{lineno} IMAGE_TAG=latest")
    # The deploy job must keep its refuse-to-apply guard.
    cd = read(".github/workflows/cd.yml")
    if "refusing to deploy" not in cd:
        problems.append(".github/workflows/cd.yml: :latest deploy guard missing")
    record("deploy path never references :latest (deduction -8)", problems)


# --------------------------------------------------- 10. Postgres stateful + PVC
def check_postgres_pvc() -> None:
    problems: list[str] = []
    for path in sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "k8s").rglob("*.yaml")):
        for doc in yaml_docs(path):
            kind = re.search(r"^kind:\s*(\S+)", doc, re.MULTILINE)
            if not kind:
                continue
            is_postgres = re.search(r"image:.*postgres", doc) is not None
            if not is_postgres:
                continue
            has_pvc = ("persistentVolumeClaim" in doc) or ("volumeClaimTemplates" in doc)
            if kind.group(1) == "Deployment" and not has_pvc:
                problems.append(f"{path}: postgres runs as Deployment without a PVC (use StatefulSet)")
            if kind.group(1) == "StatefulSet" and not has_pvc:
                problems.append(f"{path}: StatefulSet lacks volumeClaimTemplates")
    record("Postgres stateful with PVC (deduction -8)", problems)


# ----------------------------------------------- 11. nothing pushed straight to main
def check_no_direct_main() -> None:
    problems: list[str] = []
    git("fetch", "--quiet", "origin", "dev", "main")
    ahead = git("rev-list", "origin/main", "--not", "origin/dev", "--count")
    if not ahead.isdigit() or int(ahead) != 0:
        problems.append(f"{ahead or '?'} commit(s) on origin/main not reachable from origin/dev")
    record("no direct commits to main (deduction -5)", problems)


# --------------------------------------------------- 12. README quickstart works
def check_readme_quickstart() -> None:
    problems: list[str] = []
    if not (ROOT / "README.md").exists():
        problems.append("README.md missing")
        record("README quickstart references real files (deduction -5)", problems)
        return
    text = read("README.md")
    m = re.search(r"## Quickstart\s*```bash\n(.*?)```", text, re.DOTALL)
    if not m:
        problems.append("no Quickstart bash block found")
    else:
        block = m.group(1)
        for ref in re.findall(r"docker compose -f (\S+)", block):
            if not (ROOT / ref).exists():
                problems.append(f"quickstart references missing file: {ref}")
        for ref in re.findall(r"(?:\./)?scripts/([A-Za-z0-9_./-]+)", block):
            if not (ROOT / "scripts" / ref).exists():
                problems.append(f"quickstart references missing script: scripts/{ref}")
        if not re.search(r"(?:^|\s)cp \.env\.example ", block, re.MULTILINE):
            problems.append("quickstart does not bootstrap .env from .env.example")
    for name in ("compose.yaml", "compose.stub.yaml"):
        if not (ROOT / name).exists():
            problems.append(f"expected {name} missing")
    record("README quickstart references real files (deduction -5)", problems)


def main() -> int:
    check_env_history()
    check_secrets_tracked()
    check_k8s_secrets()
    check_pinned_images()
    check_localhost_s2s()
    check_frontend_db()
    check_db_cache_ports()
    check_gated_jobs()
    check_no_latest_deploy()
    check_postgres_pvc()
    check_no_direct_main()
    check_readme_quickstart()

    for name in PASSES:
        print(f"PASS  {name}")
    for name, problems in FAILURES:
        print(f"FAIL  {name}")
        for p in problems:
            print(f"        - {p}")
    print()
    if FAILURES:
        print(f"{len(FAILURES)} deduction(s) would fire — fix before submission.")
        return 1
    print("All submission-gate checks clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
