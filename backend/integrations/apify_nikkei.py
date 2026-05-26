"""

Nikkei Asia article scraper via Apify (xtracto/nikkei-scraper).



Optional fallback when own scraper returns thin content.

https://apify.com/xtracto/nikkei-scraper/api

"""

from __future__ import annotations



import logging

from typing import Any



import httpx



from app.config import settings

from integrations.nikkei_common import is_nikkei_url, normalize_article



logger = logging.getLogger(__name__)



APIFY_ACTOR = "xtracto~nikkei-scraper"

APIFY_RUN_SYNC = (

    f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"

)





def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:

    return normalize_article(raw, provider="apify_nikkei")





class NikkeiApifyService:

    """Scrape Nikkei Asia articles via Apify Actor."""



    def __init__(self, api_token: str | None = None):

        self.api_token = (api_token or settings.APIFY_API_TOKEN or "").strip()



    @property

    def configured(self) -> bool:

        return bool(self.api_token)



    async def scrape_urls(self, urls: list[str], *, max_items: int = 10) -> dict[str, Any]:

        clean = [u.strip() for u in urls if u and u.strip() and is_nikkei_url(u.strip())]

        if not clean:

            return {

                "status": "error",

                "error": "Cap URL vàlida de asia.nikkei.com",

                "count": 0,

                "articles": [],

            }

        if not self.configured:

            return {

                "status": "error",

                "error": "APIFY_API_TOKEN no configurat. Afegeix la clau al .env",

                "count": 0,

                "articles": [],

            }

        return await self._run_actor({"urls": clean[:max_items]})



    async def fetch_latest(self, *, max_items: int = 10) -> dict[str, Any]:

        if not self.configured:

            return {

                "status": "error",

                "error": "APIFY_API_TOKEN no configurat. Afegeix la clau al .env",

                "count": 0,

                "articles": [],

            }

        return await self._run_actor({"mode": "latest", "maxItems": max(1, min(max_items, 25))})



    async def _run_actor(self, actor_input: dict[str, Any]) -> dict[str, Any]:

        params = {"token": self.api_token, "timeout": 120}

        try:

            async with httpx.AsyncClient(timeout=130.0) as client:

                resp = await client.post(

                    APIFY_RUN_SYNC,

                    params=params,

                    json=actor_input,

                )

                if resp.status_code == 401:

                    return {

                        "status": "error",

                        "error": "Token Apify invàlid (401)",

                        "count": 0,

                        "articles": [],

                    }

                resp.raise_for_status()

                data = resp.json()



            items: list[Any]

            if isinstance(data, list):

                items = data

            elif isinstance(data, dict):

                items = data.get("items") or data.get("data") or []

            else:

                items = []



            articles = [_normalize_item(item) for item in items if isinstance(item, dict)]

            articles = [a for a in articles if a.get("title") or a.get("url") or a.get("body")]



            return {

                "status": "success",

                "count": len(articles),

                "articles": articles,

                "provider": "apify_nikkei",

                "message": f"{len(articles)} articles Nikkei Asia (Apify)",

            }



        except httpx.TimeoutException:

            return {

                "status": "error",

                "error": "Timeout Apify (>120s). Prova amb menys URLs.",

                "count": 0,

                "articles": [],

            }

        except httpx.HTTPStatusError as exc:

            logger.error("Apify Nikkei HTTP %s: %s", exc.response.status_code, exc.response.text[:200])

            return {

                "status": "error",

                "error": f"Error Apify ({exc.response.status_code})",

                "message": exc.response.text[:200],

                "count": 0,

                "articles": [],

            }

        except Exception as exc:

            logger.error("Apify Nikkei error: %s", exc)

            return {

                "status": "error",

                "error": "No s'ha pogut executar el scraper Nikkei",

                "message": str(exc),

                "count": 0,

                "articles": [],

            }


