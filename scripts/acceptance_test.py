#!/usr/bin/env python3
"""Phase 0 acceptance test: ingest a real repo and verify why-query citations."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import httpx

DEFAULT_REPO = "https://github.com/pallets/click"
DEFAULT_QUESTIONS = [
    "Why does the echo command work the way it does?",
    "Why is the Context class structured this way?",
    "Why does the pass_context decorator exist?",
]


async def wait_for_job(client: httpx.AsyncClient, job_id: str, timeout: int = 1800) -> dict:
    for _ in range(timeout // 5):
        resp = await client.get(f"/jobs/{job_id}")
        resp.raise_for_status()
        job = resp.json()
        print(f"  status={job['status']} files={job['files_processed']}/{job['total_files']} "
              f"cognee={job.get('cognee_status')}")
        if job["status"] in ("completed", "failed"):
            return job
        await asyncio.sleep(5)
    raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https://github\.com/[\w.-]+/[\w.-]+/(?:commit|pull|issues)/[\w?=#.-]+", text)


async def verify_url(client: httpx.AsyncClient, url: str) -> bool:
  try:
      r = await client.head(url, follow_redirects=True, timeout=15.0)
      return r.status_code < 400
  except Exception:
      return False


async def run_acceptance(api_base: str, repo_url: str, questions: list[str]) -> int:
    api_base = api_base.rstrip("/")
    print(f"Acceptance test against {api_base}")
    print(f"Repo: {repo_url}")

    async with httpx.AsyncClient(base_url=api_base, timeout=120.0) as client:
        health = await client.get("/health")
        health.raise_for_status()
        print("OK Backend healthy")

        connect = await client.post("/repos/connect", json={"url": repo_url})
        connect.raise_for_status()
        data = connect.json()
        repo_id = data["repo_id"]
        job_id = data["job_id"]
        print(f"OK Dry-run: {data['dry_run']['file_count']} files, "
              f"~${data['dry_run']['estimated_cost_usd']:.2f}")

        ingest = await client.post(f"/repos/{repo_id}/ingest", json={"job_id": job_id})
        ingest.raise_for_status()
        print("OK Ingestion confirmed, polling...")

        job = await wait_for_job(client, job_id)
        if job["status"] != "completed":
            print(f"FAIL Ingestion failed: {job.get('error_message')}")
            return 1
        print("OK Ingestion completed")

        failures = 0
        async with httpx.AsyncClient(timeout=15.0) as gh_client:
            for i, question in enumerate(questions, 1):
                print(f"\nQuestion {i}: {question}")
                resp = await client.post("/query/why", json={"repo_id": repo_id, "question": question})
                resp.raise_for_status()
                result = resp.json()
                answer = result.get("answer", "")
                evidence = result.get("evidence_chain", [])
                print(f"  Answer length: {len(answer)} chars, evidence items: {len(evidence)}")

                urls = list({e["url"] for e in evidence if e.get("url")})
                urls += extract_urls(answer)
                urls = list(dict.fromkeys(urls))

                if not urls:
                    print("  FAIL No citation URLs found")
                    failures += 1
                    continue

                for url in urls:
                    ok = await verify_url(gh_client, url)
                    status = "OK" if ok else "FAIL"
                    print(f"  {status} {url}")
                    if not ok:
                        failures += 1

        if failures:
            print(f"\nFAIL Acceptance test failed with {failures} citation errors")
            return 1

        print("\nOK Acceptance test passed - all citations resolve")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Code Archaeologist acceptance test")
    parser.add_argument("--api", default=os.getenv("API_URL", "http://localhost:8000/api"))
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--questions", nargs="*", default=DEFAULT_QUESTIONS)
    args = parser.parse_args()
    sys.exit(asyncio.run(run_acceptance(args.api, args.repo, args.questions)))


if __name__ == "__main__":
    main()
