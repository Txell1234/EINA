import asyncio

from integrations.tavily_api import TavilyAPIService


async def main() -> None:
    svc = TavilyAPIService()
    print("configured:", svc.configured())
    r = await svc.search("Japan defense spending 2025", max_results=2, topic="news")
    print("search:", r.get("status"), "count:", r.get("count"))
    if r.get("articles"):
        print("title:", r["articles"][0].get("title", "")[:80])


if __name__ == "__main__":
    asyncio.run(main())
