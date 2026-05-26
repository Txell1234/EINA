"""
Tavily REST API — Search, Extract, Crawl, Map, Research (https://docs.tavily.com).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TAVILY_BASE_URL = "https://api.tavily.com"
TAVILY_SEARCH_URL = f"{TAVILY_BASE_URL}/search"
TAVILY_EXTRACT_URL = f"{TAVILY_BASE_URL}/extract"
TAVILY_CRAWL_URL = f"{TAVILY_BASE_URL}/crawl"
TAVILY_MAP_URL = f"{TAVILY_BASE_URL}/map"
TAVILY_RESEARCH_URL = f"{TAVILY_BASE_URL}/research"


class TavilyAPIService:
    def configured(self) -> bool:
        key = (getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        return bool(key and not key.startswith("your-"))

    def _api_key(self) -> str:
        key = (getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        if not key or key.startswith("your-"):
            raise ValueError(
                "TAVILY_API_KEY no configurada. Afegeix-la al fitxer .env del backend."
            )
        return key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    async def _post(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        timeout: float = 60.0,
        accept_status: set[int] | None = None,
    ) -> tuple[int, dict[str, Any] | list[Any] | None, str]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                if accept_status and resp.status_code in accept_status:
                    try:
                        return resp.status_code, resp.json(), ""
                    except Exception:
                        return resp.status_code, None, resp.text[:300]
                resp.raise_for_status()
                return resp.status_code, resp.json(), ""
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300] if exc.response else str(exc)
            code = exc.response.status_code if exc.response else 0
            logger.error("Tavily POST %s HTTP %s: %s", url, code, detail)
            return code, None, detail
        except Exception as exc:
            logger.error("Tavily POST %s failed: %s", url, exc)
            return 0, None, str(exc)

    async def _get(
        self,
        url: str,
        *,
        timeout: float = 60.0,
        accept_status: set[int] | None = None,
    ) -> tuple[int, dict[str, Any] | None, str]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=self._headers())
                if accept_status and resp.status_code in accept_status:
                    try:
                        data = resp.json()
                        return resp.status_code, data if isinstance(data, dict) else None, ""
                    except Exception:
                        return resp.status_code, None, resp.text[:300]
                resp.raise_for_status()
                data = resp.json()
                return resp.status_code, data if isinstance(data, dict) else None, ""
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300] if exc.response else str(exc)
            code = exc.response.status_code if exc.response else 0
            logger.error("Tavily GET %s HTTP %s: %s", url, code, detail)
            return code, None, detail
        except Exception as exc:
            logger.error("Tavily GET %s failed: %s", url, exc)
            return 0, None, str(exc)

    @staticmethod
    def _error_response(
        error: str,
        message: str = "",
        *,
        provider: str = "tavily",
    ) -> dict[str, Any]:
        return {
            "status": "error",
            "error": error,
            "message": message or error,
            "count": 0,
            "articles": [],
            "provider": provider,
        }

    @staticmethod
    def _articles_from_crawl_results(results: list[Any]) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        for item in results:
            if isinstance(item, str) and item.strip().startswith("http"):
                articles.append(
                    {
                        "title": item.strip(),
                        "url": item.strip(),
                        "summary": "",
                        "body": "",
                        "source": "tavily_crawl",
                        "provider": "tavily_crawl",
                    }
                )
                continue
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            raw = str(item.get("raw_content") or item.get("content") or "").strip()
            title = str(item.get("title") or url).strip()
            if not url and not title:
                continue
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "summary": raw[:500] if raw else "",
                    "body": raw,
                    "source": "tavily_crawl",
                    "provider": "tavily_crawl",
                }
            )
        return articles

    @staticmethod
    def _articles_from_map_results(results: list[Any]) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        for item in results:
            url = str(item).strip() if isinstance(item, str) else str(item.get("url") or "").strip()
            if not url:
                continue
            if not url.startswith("http"):
                url = f"https://{url.lstrip('/')}"
            articles.append(
                {
                    "title": url,
                    "url": url,
                    "summary": "",
                    "body": "",
                    "source": "tavily_map",
                    "provider": "tavily_map",
                }
            )
        return articles

    @staticmethod
    def _articles_from_research_sources(sources: list[Any]) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or url).strip()
            if not url and not title:
                continue
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "summary": "",
                    "body": "",
                    "source": "tavily_research",
                    "provider": "tavily_research",
                }
            )
        return articles

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        search_depth: str = "advanced",
        topic: str = "general",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_answer: bool = False,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return self._error_response("Consulta Tavily buida", "Consulta buida")

        max_results = max(1, min(int(max_results), 20))
        payload: dict[str, Any] = {
            "query": q,
            "max_results": max_results,
            "search_depth": search_depth if search_depth in ("basic", "advanced") else "advanced",
            "topic": topic if topic in ("general", "news", "finance") else "general",
            "include_answer": include_answer,
        }
        if include_domains:
            payload["include_domains"] = include_domains[:20]
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains[:20]

        _, data, err = await self._post(TAVILY_SEARCH_URL, payload, timeout=60.0)
        if not data or not isinstance(data, dict):
            return self._error_response(
                f"Tavily search error",
                err or "Resposta buida",
            )

        articles: list[dict[str, Any]] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            content = str(item.get("content") or item.get("raw_content") or "").strip()
            pub_date = str(
                item.get("published_date")
                or item.get("publishedDate")
                or item.get("date")
                or ""
            ).strip()
            if not url and not title:
                continue
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "summary": content[:500] if content else "",
                    "body": content,
                    "date": pub_date,
                    "published_date": pub_date,
                    "source": "tavily",
                    "score": item.get("score"),
                    "provider": "tavily",
                }
            )

        return {
            "status": "success",
            "query_used": q,
            "count": len(articles),
            "articles": articles,
            "provider": "tavily",
            "answer": data.get("answer") if include_answer else None,
            "search_depth": payload["search_depth"],
            "topic": payload["topic"],
        }

    async def extract(
        self,
        urls: list[str],
        *,
        extract_depth: str = "basic",
        format: str = "markdown",
    ) -> dict[str, Any]:
        """Extract full page content via Tavily Extract API."""
        clean = [u.strip() for u in urls if u and str(u).strip().startswith("http")]
        if not clean:
            return self._error_response(
                "Cap URL vàlida per extreure",
                provider="tavily_extract",
            )

        payload: dict[str, Any] = {
            "urls": clean[:10],
            "extract_depth": extract_depth if extract_depth in ("basic", "advanced") else "basic",
            "format": format if format in ("markdown", "text") else "markdown",
        }

        _, data, err = await self._post(TAVILY_EXTRACT_URL, payload, timeout=90.0)
        if not data or not isinstance(data, dict):
            return self._error_response(
                "Tavily extract error",
                err or "Resposta buida",
                provider="tavily_extract",
            )

        articles: list[dict[str, Any]] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            raw = str(item.get("raw_content") or item.get("content") or "").strip()
            if not url or not raw:
                continue
            articles.append(
                {
                    "url": url,
                    "body": raw,
                    "summary": raw[:500],
                    "title": str(item.get("title") or "").strip(),
                    "provider": "tavily_extract",
                    "enrichment_source": "tavily_extract",
                    "source": "tavily_extract",
                }
            )

        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "tavily_extract",
        }

    async def crawl(
        self,
        url: str,
        *,
        instructions: str | None = None,
        max_depth: int = 1,
        max_breadth: int = 20,
        limit: int = 50,
        extract_depth: str = "basic",
        format: str = "markdown",
    ) -> dict[str, Any]:
        """Crawl a website via Tavily Crawl API."""
        root = (url or "").strip()
        if not root:
            return self._error_response("URL buida per crawl", provider="tavily_crawl")

        payload: dict[str, Any] = {
            "url": root,
            "max_depth": max(1, min(int(max_depth), 5)),
            "max_breadth": max(1, min(int(max_breadth), 500)),
            "limit": max(1, min(int(limit), 500)),
            "extract_depth": extract_depth if extract_depth in ("basic", "advanced") else "basic",
            "format": format if format in ("markdown", "text") else "markdown",
            "allow_external": True,
            "timeout": 150,
        }
        if instructions and instructions.strip():
            payload["instructions"] = instructions.strip()

        _, data, err = await self._post(TAVILY_CRAWL_URL, payload, timeout=180.0)
        if not data or not isinstance(data, dict):
            return self._error_response(
                "Tavily crawl error",
                err or "Resposta buida",
                provider="tavily_crawl",
            )

        results = data.get("results") or []
        articles = self._articles_from_crawl_results(results if isinstance(results, list) else [])
        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "tavily_crawl",
            "base_url": data.get("base_url") or root,
            "request_id": data.get("request_id"),
            "response_time": data.get("response_time"),
        }

    async def map_site(
        self,
        url: str,
        *,
        instructions: str | None = None,
        max_depth: int = 1,
        max_breadth: int = 20,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Map site URLs via Tavily Map API."""
        root = (url or "").strip()
        if not root:
            return self._error_response("URL buida per map", provider="tavily_map")

        payload: dict[str, Any] = {
            "url": root,
            "max_depth": max(1, min(int(max_depth), 5)),
            "max_breadth": max(1, min(int(max_breadth), 500)),
            "limit": max(1, min(int(limit), 500)),
            "allow_external": True,
            "timeout": 150,
        }
        if instructions and instructions.strip():
            payload["instructions"] = instructions.strip()

        _, data, err = await self._post(TAVILY_MAP_URL, payload, timeout=180.0)
        if not data or not isinstance(data, dict):
            return self._error_response(
                "Tavily map error",
                err or "Resposta buida",
                provider="tavily_map",
            )

        results = data.get("results") or []
        articles = self._articles_from_map_results(results if isinstance(results, list) else [])
        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "tavily_map",
            "base_url": data.get("base_url") or root,
            "request_id": data.get("request_id"),
            "response_time": data.get("response_time"),
        }

    async def create_research(
        self,
        input_text: str,
        *,
        model: str = "auto",
        citation_format: str = "numbered",
    ) -> dict[str, Any]:
        """Create async research task (POST /research)."""
        text = (input_text or "").strip()
        if not text:
            return self._error_response("Input de recerca buit", provider="tavily_research")

        payload: dict[str, Any] = {
            "input": text,
            "model": model if model in ("mini", "pro", "auto") else "auto",
            "stream": False,
            "citation_format": citation_format
            if citation_format in ("numbered", "mla", "apa", "chicago")
            else "numbered",
        }

        status_code, data, err = await self._post(
            TAVILY_RESEARCH_URL,
            payload,
            timeout=60.0,
            accept_status={201, 200},
        )
        if not data or not isinstance(data, dict):
            return self._error_response(
                "Tavily research error",
                err or f"HTTP {status_code}",
                provider="tavily_research",
            )

        return {
            "status": "success",
            "provider": "tavily_research",
            "research_status": data.get("status") or "pending",
            "request_id": data.get("request_id"),
            "input": data.get("input") or text,
            "model": data.get("model"),
            "created_at": data.get("created_at"),
            "count": 0,
            "articles": [],
        }

    async def get_research(self, request_id: str) -> dict[str, Any]:
        """Get research task status and results (GET /research/{request_id})."""
        rid = (request_id or "").strip()
        if not rid:
            return self._error_response("request_id buit", provider="tavily_research")

        url = f"{TAVILY_RESEARCH_URL}/{rid}"
        status_code, data, err = await self._get(
            url,
            timeout=60.0,
            accept_status={200, 202},
        )
        if not data:
            return self._error_response(
                "Tavily get research error",
                err or f"HTTP {status_code}",
                provider="tavily_research",
            )

        task_status = str(data.get("status") or "unknown")
        if task_status in ("pending", "in_progress"):
            return {
                "status": "success",
                "provider": "tavily_research",
                "research_status": task_status,
                "request_id": data.get("request_id") or rid,
                "count": 0,
                "articles": [],
                "pending": True,
            }

        if task_status == "failed":
            return {
                "status": "error",
                "error": "Tavily research task failed",
                "provider": "tavily_research",
                "research_status": "failed",
                "request_id": data.get("request_id") or rid,
                "count": 0,
                "articles": [],
            }

        sources = data.get("sources") or []
        articles = self._articles_from_research_sources(sources if isinstance(sources, list) else [])
        content = data.get("content")
        report_text = content if isinstance(content, str) else ""
        if not report_text and isinstance(content, dict):
            report_text = str(content)

        return {
            "status": "success",
            "provider": "tavily_research",
            "research_status": "completed",
            "request_id": data.get("request_id") or rid,
            "count": len(articles),
            "articles": articles,
            "research_report": report_text,
            "sources": sources,
            "created_at": data.get("created_at"),
            "pending": False,
        }

    async def research_and_wait(
        self,
        input_text: str,
        *,
        model: str = "auto",
        max_wait_seconds: int = 300,
        poll_interval: float = 5.0,
    ) -> dict[str, Any]:
        """Create research task and poll until completed or timeout."""
        created = await self.create_research(input_text, model=model)
        if created.get("status") != "success":
            return created

        request_id = str(created.get("request_id") or "")
        if not request_id:
            return self._error_response(
                "Tavily research sense request_id",
                provider="tavily_research",
            )

        deadline = time.monotonic() + max(30, int(max_wait_seconds))
        while time.monotonic() < deadline:
            result = await self.get_research(request_id)
            if result.get("status") == "error":
                return result
            if not result.get("pending"):
                return result
            await asyncio.sleep(max(2.0, poll_interval))

        return {
            "status": "success",
            "provider": "tavily_research",
            "research_status": "timeout",
            "request_id": request_id,
            "count": 0,
            "articles": [],
            "pending": True,
            "message": "Recerca encara en curs — consulta l'estat amb request_id",
        }
