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
    js.add_argument("query", help="Search query, e.g. 'python developer remote'")
    js.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    if args.cmd == "health":
        asyncio.run(health())
    elif args.cmd == "jobs":
        asyncio.run(job_search(args.query, args.limit))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
