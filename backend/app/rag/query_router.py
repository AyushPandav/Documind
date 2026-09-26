import re
import logging
from typing import List, Dict, Any, Optional
from app.rag.language_service import detect_language, translate_query_for_retrieval

logger = logging.getLogger("DocuMind.QueryRouter")


class RoutingDecision:
    def __init__(
        self,
        need_documents: bool = True,
        need_web_search: bool = False,
        need_live_api: Optional[str] = None,  # "time" | "weather" | "crypto" | "forex"
        document_query: Optional[str] = None,
        web_query: Optional[str] = None,
        reasoning: str = ""
    ):
        self.need_documents = need_documents
        self.need_web_search = need_web_search
        self.need_live_api = need_live_api
        self.document_query = document_query
        self.web_query = web_query
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "need_documents": self.need_documents,
            "need_web_search": self.need_web_search,
            "need_live_api": self.need_live_api,
            "document_query": self.document_query,
            "web_query": self.web_query,
            "reasoning": self.reasoning,
        }


class IntelligentQueryRouter:
    """
    Intelligent Hybrid Query Router:
    Routes incoming user queries to appropriate retrieval pipelines:
    - Internal Document Knowledge Base (Vector DB / BM25)
    - Live Web Search (DuckDuckGo)
    - Real-time APIs (System Clock, Weather, Crypto, Forex)
    """

    def __init__(self):
        # Time patterns
        self.time_patterns = [
            r"\b(?:what(?:\s+is|\s+'s)?\s+(?:the\s+)?(?:current\s+)?time)\b",
            r"\b(?:what(?:\s+is|\s+'s)?\s+today(?:'s)?\s+date)\b",
            r"\b(?:current\s+time)\b",
            r"\b(?:what\s+day\s+is\s+(?:it|today))\b",
            r"\b(?:today(?:'s)?\s+date)\b"
        ]

        # Weather patterns
        self.weather_patterns = [
            r"\b(?:weather|temperature|forecast|is\s+it\s+raining)\b"
        ]

        # Crypto patterns
        self.crypto_patterns = [
            r"\b(?:bitcoin|btc|ethereum|eth|solana|crypto(?:currency)?|doge(?:coin)?)\b.*?\b(?:price|rate|worth|market|value)\b",
            r"\b(?:price|rate|worth|value)\s+of\s+(?:bitcoin|btc|ethereum|eth|solana|doge)\b"
        ]

        # Currency / Forex patterns
        self.forex_patterns = [
            r"\b(?:exchange\s+rate|forex|currency\s+rate|usd\s+to\s+inr|dollar\s+to\s+rupee|euro\s+to\s+dollar)\b"
        ]

        # Web search triggers
        self.web_search_triggers = [
            # English
            "latest", "today", "current", "news", "recent", "stock price", "share price",
            "market cap", "ceo of", "who is", "who won", "current president",
            "release date", "search the web", "search online", "google", "live", "updated",
            "now", "2025", "2026", "world news", "current price",
            # Hindi equivalents
            "ताज़ा", "अभी", "वर्तमान", "खबर", "समाचार", "हालिया",
            "स्टॉक मूल्य", "शेयर मूल्य", "लाइव", "अपडेट"
        ]

        # Internal document triggers (English + Hindi)
        self.doc_triggers = [
            # English
            "document", "doc", "pdf", "file", "uploaded", "report", "manual",
            "page", "policy", "handbook", "contract", "section", "table", "sheet",
            "according to the", "in the file", "in this document", "our company",
            # Hindi equivalents
            "दस्तावेज़", "फ़ाइल", "रिपोर्ट", "पृष्ठ", "पेज", "नीति", "अनुबंध",
            "अनुभाग", "तालिका", "इस दस्तावेज़ में", "हमारी कंपनी", "अपलोड"
        ]

        # Hindi time patterns
        self.hindi_time_patterns = [
            r"(?:अभी का|\s+)समय",
            r"आज की तारीख",
            r"क्या समय है",
            r"आज क्या दिन है",
        ]

        # Hindi weather patterns
        self.hindi_weather_patterns = [
            r"मौसम",
            r"तापमान",
            r"बारिश",
            r"हवा",
        ]

    def route(
        self,
        query: str,
        has_uploaded_docs: bool = True,
        doc_filter: Optional[str] = None
    ) -> RoutingDecision:
        """
        Analyzes query intent, routing to one or more retrieval sources.
        """
        q_lower = query.lower().strip()
        query_lang = detect_language(query)
        logger.info(f"[QueryRouter] Detected query language: {query_lang.upper()}")

        # 1. Check for Live APIs (English patterns)
        live_api = None
        for pat in self.time_patterns:
            if re.search(pat, q_lower):
                live_api = "time"
                break

        # Check Hindi time patterns
        if not live_api:
            for pat in self.hindi_time_patterns:
                if re.search(pat, query):
                    live_api = "time"
                    break

        if not live_api:
            for pat in self.weather_patterns:
                if re.search(pat, q_lower):
                    live_api = "weather"
                    break

        # Check Hindi weather patterns
        if not live_api:
            for pat in self.hindi_weather_patterns:
                if re.search(pat, query):
                    live_api = "weather"
                    break

        if not live_api:
            for pat in self.crypto_patterns:
                if re.search(pat, q_lower):
                    live_api = "crypto"
                    break

        if not live_api:
            for pat in self.forex_patterns:
                if re.search(pat, q_lower):
                    live_api = "forex"
                    break

        # 2. Check for explicit doc references
        has_doc_trigger = any(t in q_lower for t in self.doc_triggers) or bool(doc_filter)

        # 3. Check for web search triggers
        has_web_trigger = any(t in q_lower for t in self.web_search_triggers)

        # If pure live api query and no document context requested:
        if live_api and not has_doc_trigger and not doc_filter:
            logger.info(f"[QueryRouter] 🕐 Route: LIVE_API ({live_api})")
            return RoutingDecision(
                need_documents=False,
                need_web_search=False,
                need_live_api=live_api,
                reasoning=f"Query directly targets live API ({live_api})"
            )

        # 4. Multi-Source Hybrid Routing:
        # e.g., "According to our company's 2024 financial report, what was the revenue, and what is the company's current stock price?"
        is_hybrid = False
        doc_q = query
        web_q = query

        if has_doc_trigger and (has_web_trigger or live_api):
            is_hybrid = True
            logger.info(f"[QueryRouter] 🔀 Route: HYBRID (Documents + Web/API)")

            # Try to decompose clauses if separated by 'and', 'also', 'while', comma
            parts = re.split(r'\b(?:and|also|while|along\s+with)\b', query, flags=re.IGNORECASE)
            if len(parts) >= 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                if any(t in p1.lower() for t in self.doc_triggers):
                    doc_q = p1
                    web_q = p2
                elif any(t in p2.lower() for t in self.doc_triggers):
                    doc_q = p2
                    web_q = p1

            return RoutingDecision(
                need_documents=True,
                need_web_search=True,
                need_live_api=live_api,
                document_query=doc_q,
                web_query=web_q,
                reasoning="Multi-source query requires internal documents + external live evidence"
            )

        # 5. External Web Search Route:
        if has_web_trigger and not has_doc_trigger:
            logger.info(f"[QueryRouter] 🌐 Route: WEB_SEARCH (DuckDuckGo)")
            return RoutingDecision(
                need_documents=False,
                need_web_search=True,
                need_live_api=live_api,
                document_query=None,
                web_query=query,
                reasoning="Query asks for current, external, or live information without referencing documents"
            )

        # 6. Default: Document RAG Route
        logger.info(f"[QueryRouter] 📄 Route: INTERNAL_DOCUMENTS (Hybrid BM25 + Vector)")
        return RoutingDecision(
            need_documents=True,
            need_web_search=False,
            need_live_api=None,
            document_query=query,
            web_query=None,
            reasoning="Query addresses indexed document repository"
        )


query_router = IntelligentQueryRouter()
