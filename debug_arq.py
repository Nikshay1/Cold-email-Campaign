import asyncio
import redis.asyncio as aioredis
from arq.jobs import deserialize_job

async def main():
    redis = await aioredis.from_url("redis://localhost:6379/0", decode_responses=False)
    jobs = await redis.zrange("arq:queue", 0, -1, withscores=True)
    for job, score in jobs:
        try:
            j = deserialize_job(job)
            print(f"Scheduled for {score}: Func={j.function}, Args={j.args}, DeferBy={j.defer_until}")
        except Exception as e:
            print(f"Err {e}")

if __name__ == "__main__":
    asyncio.run(main())
