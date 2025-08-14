import json
import tempfile
from pathlib import Path

from scripts.import_graphrag_artifacts import main as import_main


def write_csv(path: Path, name: str, header: str, rows: list[str]):
    f = path / name
    with f.open('w') as fh:
        fh.write(header + "\n")
        for r in rows:
            fh.write(r + "\n")
    return f


def test_import_graphrag_dry_run(monkeypatch):
    # Create synthetic artifact directory
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        write_csv(base, 'entities.csv', 'entity_id,name,type,description', [
            'e1,Alpha,Company,Alpha company',
            'e2,Beta,Person,Beta person'
        ])
        write_csv(base, 'relationships.csv', 'relationship_id,src_id,dst_id,relationship_type,weight', [
            'r1,e1,e2,FOUNDED_BY,0.9'
        ])
        write_csv(base, 'communities.csv', 'community_id,entity_id', [
            'c1,e1',
            'c1,e2'
        ])
        write_csv(base, 'community_reports.csv', 'community_id,report_title,report_summary', [
            'c1,Cluster C1,This is a test summary'
        ])
        # Patch sys.argv for dry run
        import sys
        old = sys.argv
        try:
            sys.argv = ['import_graphrag_artifacts', '--path', str(base), '--dry-run']
            exit_code = import_main()
            assert exit_code == 0
        finally:
            sys.argv = old
