from scripts.run_graphrag_index import orchestrate


def test_delta_metrics_present():
    res = orchestrate(namespace="public", force=False, dry_run=True)
    assert 'stale_docs' in res
    assert 'total_docs' in res
    assert res['stale_docs'] <= res['total_docs']
