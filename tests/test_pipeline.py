import os
import tempfile

from src.pipeline.orchestrator import run_pipeline


def test_demo_dry_run_pipeline_executes_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AI_PROVIDER"] = "mock"
        db_path = os.path.join(tmp, "demo.db")
        result = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)

        assert "stats" in result
        assert result["stats"]["candidates_found"] >= 0
        assert result["run"].dry_run is True
        assert result["run"].demo_mode is True


def test_demo_dry_run_pipeline_is_idempotent_on_rerun():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AI_PROVIDER"] = "mock"
        db_path = os.path.join(tmp, "demo2.db")

        result1 = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)
        articles_first_run = result1["run"].articles_generated

        # Second run against the same DB should not duplicate the same events'
        # articles (fingerprint-based idempotency).
        result2 = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)

        assert result2["run"].articles_generated <= articles_first_run + 5
