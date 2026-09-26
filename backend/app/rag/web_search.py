import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("DocuMind.WebSearch")


class WebSearchRetriever:
    """
    Live Web Search Retriever using DuckDuckGo.
    Provides external world knowledge and up-to-date facts.
    """

    def __init__(self, max_results: int = 4, timeout: float = 8.0):
        self.max_results = max_results
        self.timeout = timeout

    async def search(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Asynchronously searches the web and returns structured evidence chunks.
        """
        k = max_results or self.max_results
        results: List[Dict[str, Any]] = []

        # Sanitize query for web search
        clean_query = query.strip()
        if not clean_query:
            return []

        logger.info(f"[WebSearch] 🌐 Searching web for: '{clean_query}' (limit={k})")

        try:
            import asyncio
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            def _sync_ddgs_search():
                try:
                    with DDGS(timeout=self.timeout) as ddgs:
                        raw = list(ddgs.text(clean_query, max_results=k))
                        return raw
                except Exception as ex:
                    logger.warning(f"[WebSearch] DDGS call exception: {ex}")
                    return []

            loop = asyncio.get_running_loop()
            raw_results = await loop.run_in_executor(None, _sync_ddgs_search)

            now_iso = datetime.now(timezone.utc).isoformat()

            for idx, item in enumerate(raw_results):
                title = item.get("title", "").strip() or "Web Source"
                snippet = item.get("body", "").strip()
                url = item.get("href", "").strip()

                if not snippet and not title:
                    continue

                # Calculate heuristic relevance score
                relevance = max(65, 92 - (idx * 5))

                results.append({
                    "id": f"web-{uuid.uuid4().hex[:6]}",
                    "source_type": "web",
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "retrieved_at": now_iso,
                    "relevance": relevance,
                    "metadata": {
                        "source": "DuckDuckGo Search",
                        "domain": url.split("/")[2] if "//" in url else url
                    }
                })

            logger.info(f"[WebSearch] 🌐 Retrieved {len(results)} web results for '{clean_query}'")

        except Exception as e:
            logger.error(f"[WebSearch] Failed to retrieve web results: {e}", exc_info=True)

        return results


web_search_retriever = WebSearchRetriever()
