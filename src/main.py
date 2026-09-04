"""Entry point: reads env config and runs the daily pipeline once."""
from __future__ import annotations

import json
import os
import sys

from src.pipeline.orchestrator import run_pipeline


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, str(default)).strip().lower()
    return val in ("1", "true", "yes", "on")


def main() -> int:
    dry_run = _env_bool("DRY_RUN", False)
    demo_mode = _env_bool("DEMO_MODE", False)

    result = run_pipeline(dry_run=dry_run, demo_mode=demo_mode)

    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    print("Distribution:", json.dumps(result["distribution"], ensure_ascii=False, indent=2))
    if result["run"].errors > 0:
        print(f"Completed with {result['run'].errors} error(s). See logs/ for details.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
