import asyncio
import httpx

async def main() -> None:
    base = "https://backend-production-c1682.up.railway.app/api"
    async with httpx.AsyncClient(timeout=180.0) as c:
        r = await c.post(f"{base}/repos/connect", json={"url": "https://github.com/pallets/click"})
        print("connect:", r.status_code)
        if r.status_code != 200:
            print(r.text[:500])
            return
        d = r.json()
        print("dry_run files:", d["dry_run"]["file_count"])
        r2 = await c.post(f"{base}/repos/{d['repo_id']}/ingest", json={"job_id": d["job_id"]})
        print("ingest start:", r2.status_code, r2.text)
        for i in range(8):
            await asyncio.sleep(15)
            j = await c.get(f"{base}/jobs/{d['job_id']}")
            job = j.json()
            print(
                f"poll {i}: status={job['status']} "
                f"msg={job.get('progress_message')} "
                f"files={job['files_processed']}/{job['total_files']} "
                f"err={job.get('error_message')}"
            )
            if job["status"] in ("completed", "failed"):
                break

asyncio.run(main())
