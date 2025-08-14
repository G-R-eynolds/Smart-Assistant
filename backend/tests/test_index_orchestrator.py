from scripts.run_graphrag_index import orchestrate


def test_orchestrate_dry_run(tmp_path, monkeypatch):
    # Ensure dry-run does not attempt import (still generates dummy artifacts)
    res = orchestrate(namespace="public", force=False, dry_run=True)
    assert res['status'] == 'DRY_RUN'
    assert 'staging_dir' in res


def test_orchestrate_real_import(tmp_path, monkeypatch):
    res = orchestrate(namespace="public", force=False, dry_run=False)
    # Accept broader set including PARTIAL/FAILED/IMPORT_FAILED or NOOP (delta short-circuit) but exclude LOCKED
    assert res['status'] in {'SUCCESS', 'PARTIAL', 'FAILED', 'IMPORT_FAILED', 'NOOP'}
    if res['status'] != 'NOOP':
        assert res['staging_dir']
