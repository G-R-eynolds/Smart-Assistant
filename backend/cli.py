import asyncio
import json
import os

import httpx

API_BASE = os.environ.get("SMART_ASSISTANT_API", "http://localhost:8000")


async def health() -> int:
    url = f"{API_BASE}/health"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        print(json.dumps(r.json(), indent=2))
        return r.status_code


async def job_search(query: str, limit: int = 5) -> int:
    url = f"{API_BASE}/api/smart-assistant/jobs/search"
    payload = {"query": query, "limit": limit, "generate_cover_letters": False, "save_to_airtable": False}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload)
        print(json.dumps(r.json(), indent=2))
        return r.status_code


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Smart Assistant backend CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("health", help="Check backend health")

    js = sub.add_parser("jobs", help="Run a minimal job search")
    js.add_argument("query", help="Search query, e.g. 'python developer remote' ")
    js.add_argument("--limit", type=int, default=5)

    igr = sub.add_parser("import-graphrag", help="Import GraphRAG artifacts into local graph store (Phase 1)")
    igr.add_argument("--path", required=True, help="Directory containing GraphRAG artifact files")
    igr.add_argument("--namespace", default="public")
    igr.add_argument("--dry-run", action="store_true")

    ir = sub.add_parser("index-run", help="Run GraphRAG batch index orchestrator (Phase 2 skeleton)")
    ir.add_argument("--namespace", default="public")
    ir.add_argument("--force", action="store_true")
    ir.add_argument("--dry-run", action="store_true")
    ir.add_argument("--since", default=None, help="ISO8601 timestamp cutoff (placeholder)")
    ir.add_argument("--keep", type=int, default=5, help="retain last K runs")

    args = parser.parse_args()

    if args.cmd == "health":
        asyncio.run(health())
    elif args.cmd == "jobs":
        asyncio.run(job_search(args.query, args.limit))
    elif args.cmd == "import-graphrag":
        # Defer heavy imports
        from scripts.import_graphrag_artifacts import main as import_main
        import sys as _sys
        # Simulate argparse for the script by building argv fragment
        argv = ["--path", args.path, "--namespace", args.namespace]
        if args.dry_run:
            argv.append("--dry-run")
        # Patch sys.argv temporarily
        old_argv = _sys.argv
        try:
            _sys.argv = [old_argv[0]] + argv
            _sys.exit(import_main())
        finally:
            _sys.argv = old_argv
    elif args.cmd == "index-run":
        from scripts.run_graphrag_index import main as index_main
        import sys as _sys
        argv = ["--namespace", args.namespace, "--keep", str(args.keep)]
        if args.force:
            argv.append("--force")
        if args.dry_run:
            argv.append("--dry-run")
        if args.since:
            argv += ["--since", args.since]
        old_argv = _sys.argv
        try:
            _sys.argv = [old_argv[0]] + argv
            _sys.exit(index_main())
        finally:
            _sys.argv = old_argv
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
