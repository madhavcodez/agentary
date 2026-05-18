"""Dump the FastAPI OpenAPI schema to a JSON file.

Used by the dashboard's ``generate:api-types`` script and by CI to detect
schema drift between Pydantic models and the hand-written TypeScript types
in ``dashboard/lib/types.ts``. Importing the FastAPI app at module-load
triggers the lifespan handlers in some setups — we keep that out of scope
by directly building the schema via ``app.openapi()``.

Usage:
    python -m scripts.dump_openapi [output_path]

If no path is supplied, writes to ``backend/openapi.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    # Import inside main so importing the module for tooling does not
    # boot the FastAPI app's lifespan unintentionally.
    from app.main import app

    output = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / "openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote OpenAPI schema to {output} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
