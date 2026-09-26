"""Export the FastAPI OpenAPI document to docs/openapi.json.

Deterministic and idempotent: run it, commit the result, run it again and git
diff stays empty.

Two conformances over FastAPI's natural output, both required by the frozen
contract (docs/openapi.json, handoff \u00a71):

1. URL semantics: the contract documents paths relative to ``servers: /api``
   (the frontend proxies /api \u2014 ADR 0002), so ``/api/complaints`` is written
   as ``/complaints``. Root-level paths (/health, /ready, /metrics) override
   the server back to ``/``.
2. Status codes: routes/errors.py maps every RequestValidationError to 400
   with field-level detail, so the runtime never emits FastAPI's default 422.
   The 422 responses are dropped, and components.schemas.ValidationError is
   forced back to the contract shape \u2014 FastAPI's internal model of the same
   name (loc/msg/type/input, used by its 422 body) would otherwise win the
   collision and silently redefine the 400 bodies too.
"""

import json
import sys
from pathlib import Path

from app import schemas
from app.main import app

SERVERS = [
    {"url": "/api", "description": "Relative \u2014 frontend proxies /api (ADR 0002)"}
]
ROOT_PATHS = {"/health", "/ready", "/metrics"}


def build_spec() -> dict:
    spec = app.openapi()
    components = spec.setdefault("components", {})
    sch = components.setdefault("schemas", {})

    # 1. Drop the phantom 422; the runtime returns 400 (see routes/errors.py).
    for item in spec.get("paths", {}).values():
        for operation in item.values():
            if isinstance(operation, dict):
                operation.get("responses", {}).pop("422", None)
    sch.pop("HTTPValidationError", None)

    # 2. Force the contract-shaped ValidationError (FastAPI's same-named model
    #    is registered by its own 422 machinery and must not win).
    schema = schemas.ValidationError.model_json_schema()
    for name, definition in schema.pop("$defs", {}).items():
        sch.setdefault(name, definition)
    schema = json.loads(
        json.dumps(schema).replace("#/$defs/", "#/components/schemas/")
    )
    sch["ValidationError"] = schema

    # 3. Contract URL semantics: paths relative to servers: /api.
    paths: dict = {}
    for path, item in spec.get("paths", {}).items():
        if path.startswith("/api/"):
            paths[path[4:]] = item  # /api/complaints -> /complaints
        elif path in ROOT_PATHS:
            paths[path] = {**item, "servers": [{"url": "/"}]}
        else:
            paths[path] = item
    spec["paths"] = paths
    spec["servers"] = SERVERS
    return spec


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "../docs/openapi.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    spec = build_spec()
    target.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {target} ({len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()
