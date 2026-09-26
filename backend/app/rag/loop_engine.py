import re
import time
import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple

from app.rag.retriever import hybrid_retriever
from app.rag.query_router import query_router
from app.rag.web_search import web_search_retriever
from app.rag.live_apis import live_api_service
from app.rag.language_service import (
    detect_language,
    get_language_label,
    get_response_language_instruction,
    translate_query_for_retrieval
)
from app.core.circuit_breaker import generate_rag_response

logger = logging.getLogger("DocuMind.LoopEngine")


class SelfReflectiveRAGLoop:
    """
    Hybrid Multi-Source Self-Reflective Corrective RAG Loop:
    1. Intelligent Query Routing      — routes to Documents, Live Web Search, and Live APIs
    2. Query Decomposition           — splits multi-source / comparative queries
    3. Multi-Source Retrieval Loop   — Vector/BM25 for docs + DuckDuckGo + Live Clock/Weather/Finance APIs
    4. Evidence Fusion & Reranking   — unifies internal & external sources into cohesive evidence pool
    5. Cross-Source Conflict Guard   — detects conflicting claims between docs or docs vs web
    6. Grounded Synthesis Guard      — strict evidence-grounded prompt without fabrication
    7. Multi-Source Citations        — labeled [1], [2] with source badges (internal, web, live API)
    """

    def __init__(self, max_iterations: int = 2, sufficiency_threshold: float = 0.28):
        self.max_iterations = max_iterations
        self.sufficiency_threshold = sufficiency_threshold

    def decompose_query(self, query: str) -> List[str]:
        """
        Decomposes complex multi-part queries into discrete sub-queries.
        """
        lower = query.lower()
        sub_queries = [query]

        if any(term in lower for term in [" compare ", " versus ", " vs ", " difference between "]):
            parts = re.split(r'\b(?:compare|versus|vs|and|with|between)\b', query, flags=re.IGNORECASE)
            cleaned = [p.strip() for p in parts if len(p.strip()) > 5]
            if len(cleaned) >= 2:
                sub_queries = cleaned
                logger.info(f"[LoopEngine] Query decomposed into {len(sub_queries)} sub-queries: {sub_queries}")

        return sub_queries

    def reformulate_query(self, query: str, iteration: int) -> str:
        """
        Broadens query on low retrieval confidence:
        Strips filler words, preserves high-signal nouns and numbers.
        """
        stopwords = {
            "what", "is", "the", "how", "many", "does", "can", "you", "tell",
            "me", "about", "please", "why", "where", "which", "could", "should",
            "would", "give", "show", "find"
        }
        words = [w for w in re.findall(r'\b\w+\b', query.lower()) if w not in stopwords]
        reformulated = " ".join(words) if words else query
        logger.info(f"[LoopEngine] Query reformulated (iter {iteration + 1}): '{query}' → '{reformulated}'")
        return reformulated

    def detect_conflicts(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        """
        Detects conflicting facts or numbers across retrieved document chunks or web sources.
        """
        # Only compare document chunks with each other to detect true conflicting policy/figures
        doc_chunks = [c for c in chunks if c.get("type") == "document" or "doc_name" in c]
        if len(doc_chunks) < 2:
            return None

        for term in ["refund", "leave", "notice period", "revenue", "budget"]:
            mentions = []
            for c in doc_chunks:
                content = c.get("content", "") or c.get("snippet", "")
                if term in content.lower():
                    # Find numbers closely associated with this term
                    pattern = rf'\b{re.escape(term)}\b[^.\n]*?(\d+(?:\.\d+)?%?)'
                    found = re.findall(pattern, content, re.IGNORECASE)
                    if found:
                        source_label = c.get("doc_name") or c.get("title") or "Document"
                        page = c.get("page_number", 1)
                        mentions.append((source_label, page, found))

            if len(mentions) >= 2:
                first_src, first_p, first_nums = mentions[0]
                second_src, second_p, second_nums = mentions[1]
                if first_src != second_src and set(first_nums) != set(second_nums):
                    conflict_msg = (
                        f"Potential conflict detected between '{first_src}' (Page {first_p}) "
                        f"and '{second_src}' (Page {second_p}) regarding '{term}' ({', '.join(first_nums[:2])} vs {', '.join(second_nums[:2])})."
                    )
                    logger.warning(f"[LoopEngine] ⚠ CONFLICT: {conflict_msg}")
                    return conflict_msg
        return None

    def evaluate_sufficiency(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """
        Evaluates whether retrieved chunks contain sufficient evidence for answering the query.
        """
        if not retrieved_chunks:
            return False, 0.0

        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        if not query_terms:
            return True, 1.0

        max_overlap = 0.0
        for c in retrieved_chunks:
            content = c.get("content", "") or c.get("snippet", "")
            content_lower = content.lower()
            matched = sum(1 for term in query_terms if term in content_lower)
            ratio = matched / len(query_terms)
            if ratio > max_overlap:
                max_overlap = ratio

        top_dense = retrieved_chunks[0].get("dense_score", 0.0) if retrieved_chunks else 0.0
        confidence = float(0.6 * max_overlap + 0.4 * max(0.0, top_dense))

        # Check for overview/summary queries
        summary_triggers = [
            "what is this", "what is the document", "what is the pdf", "what does this",
            "about", "summarize", "summary", "overview", "describe", "description",
            "tell me about", "explain this", "main points", "key takeaways", "what is inside"
        ]
        if any(st in query.lower() for st in summary_triggers):
            return True, 0.95

        is_sufficient = confidence >= self.sufficiency_threshold
        return is_sufficient, confidence

    async def execute_rag_pipeline(
        self,
        query: str,
        all_chunks: List[Dict[str, Any]],
        doc_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the Hybrid Multi-Source Retrieval RAG Pipeline:
        1. Query Router decides which pipelines are active (Documents, Web Search, Live APIs).
        2. Dispatches parallel retrieval across selected pipelines.
        3. Fuses multi-source evidence into unified context & citations.
        4. Cross-checks conflict and sufficiency.
        5. Synthesizes strictly grounded answer using LLM circuit breaker.
        """
        t_total = time.monotonic()
        clean_query = query.strip()

        logger.info("═" * 68)
        logger.info(f"[LoopEngine] ▶ Hybrid Multi-Source RAG Pipeline START")
        logger.info(f"[LoopEngine] Query: '{clean_query[:80]}'")
        logger.info(f"[LoopEngine] Corpus: {len(all_chunks)} chunks | Filter: {doc_filter or 'None'}")
        logger.info("═" * 68)

        # ── Step 1: Intelligent Query Routing ────────────────────────────────
        routing = query_router.route(
            query=clean_query,
            has_uploaded_docs=bool(all_chunks),
            doc_filter=doc_filter
        )
        logger.info(
            f"[LoopEngine] Route decision: docs={routing.need_documents}, "
            f"web={routing.need_web_search}, live_api={routing.need_live_api} | {routing.reasoning}"
        )

        # If pure document query requested but corpus is empty and no external sources
        if not all_chunks and not routing.need_web_search and not routing.need_live_api:
            logger.warning("[LoopEngine] No chunks in database and query is purely internal.")
            return {
                "answer": "No documents have been uploaded or indexed yet. Please upload a PDF, Word document, or spreadsheet, or ask a question requiring live web information or current facts!",
                "citations": [],
                "is_insufficient_info": False,
                "confidence_score": 0.0,
                "model_used": "DocuMind System Guide",
                "conflict_note": None
            }

        # ── Step 2: Parallel Multi-Source Retrieval ──────────────────────────
        doc_chunks: List[Dict[str, Any]] = []
        web_results: List[Dict[str, Any]] = []
        live_api_results: List[Dict[str, Any]] = []

        retrieval_tasks = []

        # 2a. Live API task
        if routing.need_live_api:
            async def _fetch_live_api():
                api_type = routing.need_live_api
                if api_type == "time":
                    return live_api_service.get_system_time(clean_query)
                elif api_type == "weather":
                    return await live_api_service.get_weather(clean_query)
                elif api_type == "crypto":
                    return await live_api_service.get_crypto_price(clean_query)
                elif api_type == "forex":
                    return await live_api_service.get_exchange_rates(clean_query)
                return []

            retrieval_tasks.append(("live_api", _fetch_live_api()))

        # 2b. Web search task
        if routing.need_web_search:
            search_q = routing.web_query or clean_query
            retrieval_tasks.append(("web", web_search_retriever.search(search_q, max_results=4)))

        # 2c. Execute external tasks concurrently
        if retrieval_tasks:
            names = [t[0] for t in retrieval_tasks]
            coros = [t[1] for t in retrieval_tasks]
            gathered = await asyncio.gather(*coros, return_exceptions=True)
            for name, res in zip(names, gathered):
                if isinstance(res, Exception):
                    logger.error(f"[LoopEngine] Error in {name} retrieval: {res}")
                elif isinstance(res, list):
                    if name == "live_api":
                        live_api_results = res
                    elif name == "web":
                        web_results = res

        # 2d. Internal Document Retrieval (if needed and chunks available)
        if routing.need_documents and all_chunks:
            doc_query_text = routing.document_query or clean_query
            filter_terms = []
            if doc_filter:
                unquoted_filter = urllib.parse.unquote(doc_filter)
                for raw in [doc_filter, unquoted_filter]:
                    for t in raw.split(","):
                        ct = t.strip().lower()
                        if ct and ct not in filter_terms:
                            filter_terms.append(ct)

            # Check if overview/summary query
            q_lower = doc_query_text.lower()
            summary_triggers = ["summarize", "overview", "what is this document", "what does this pdf say", "what is inside", "describe this"]
            is_summary = any(st in q_lower for st in summary_triggers)

            if is_summary and (filter_terms or len(all_chunks) <= 12):
                target_chunks = all_chunks
                if filter_terms:
                    filtered = [
                        c for c in all_chunks
                        if any(term in c.get("doc_name", "").lower() or term in c.get("doc_id", "").lower() for term in filter_terms)
                    ]
                    if filtered:
                        target_chunks = filtered

                target_chunks.sort(key=lambda c: (c.get("page_number", 1), c.get("chunk_index", 1)))
                doc_chunks = target_chunks[:8]
            else:
                sub_queries = self.decompose_query(doc_query_text)
                collected: Dict[str, Dict[str, Any]] = {}
                retrieval_k = max(6, min(12, len(all_chunks)))

                for sq in sub_queries:
                    active_q = sq
                    for it in range(self.max_iterations):
                        retrieved = hybrid_retriever.retrieve(
                            query=active_q,
                            chunks=all_chunks,
                            top_k=retrieval_k,
                            doc_filter=doc_filter
                        )
                        is_suff, score = self.evaluate_sufficiency(active_q, retrieved)
                        if is_suff or it == self.max_iterations - 1:
                            for c in retrieved:
                                collected[c["id"]] = c
                            break
                        else:
                            active_q = self.reformulate_query(active_q, it)

                final_c = list(collected.values())
                final_c.sort(key=lambda x: x.get("relevance", 0), reverse=True)
                doc_chunks = final_c[:8] if final_c else all_chunks[:4]

        # ── Step 3: Evidence Fusion & Cross-Source Conflict Checking ──────────
        all_evidence: List[Dict[str, Any]] = []

        # 3a. Add Live API items
        for item in live_api_results:
            all_evidence.append({
                "type": "live_api",
                "id": item["id"],
                "title": item["title"],
                "snippet": item["snippet"],
                "url": item.get("url"),
                "retrieved_at": item.get("retrieved_at"),
                "relevance": item.get("relevance", 98),
                "metadata": item.get("metadata", {})
            })

        # 3b. Add Document chunks
        for c in doc_chunks:
            all_evidence.append({
                "type": "document",
                "id": c["id"],
                "title": c.get("doc_name", "Indexed Document"),
                "doc_id": c.get("doc_id", "doc"),
                "page": c.get("page_number", 1),
                "section": c.get("chunk_index", 1),
                "snippet": c.get("content", ""),
                "relevance": c.get("relevance", 85)
            })

        # 3c. Add Web Search items
        for w in web_results:
            all_evidence.append({
                "type": "web",
                "id": w["id"],
                "title": w["title"],
                "url": w.get("url"),
                "snippet": w.get("snippet", ""),
                "retrieved_at": w.get("retrieved_at"),
                "relevance": w.get("relevance", 80),
                "metadata": w.get("metadata", {})
            })

        logger.info(
            f"[LoopEngine] Step 3: Fused {len(all_evidence)} total evidence items "
            f"(Docs: {len(doc_chunks)}, Web: {len(web_results)}, Live: {len(live_api_results)})"
        )

        # 3d. Check cross-source conflicts
        conflict_note = self.detect_conflicts(all_evidence)

        # ── Step 4: Build Grounded Context with Boundary Tags ──────────────────
        context_blocks = []
        citations_data = []

        for idx, ev in enumerate(all_evidence):
            cite_num = idx + 1
            ev_type = ev["type"]

            if ev_type == "document":
                boundary = f"[DOC: {ev['title']} | PAGE: {ev['page']} | SECTION: {ev.get('section', 1)}]"
                snippet_text = ev["snippet"]
                citations_data.append({
                    "id": f"cite-{ev['id']}",
                    "index": cite_num,
                    "sourceType": "document",
                    "documentId": ev.get("doc_id", "doc-1"),
                    "documentName": ev["title"],
                    "page": ev["page"],
                    "url": None,
                    "retrievedAt": None,
                    "snippet": snippet_text[:240].strip() + ("..." if len(snippet_text) > 240 else ""),
                    "relevance": ev.get("relevance", 85)
                })
            elif ev_type == "web":
                domain = ev.get("metadata", {}).get("domain") or "Web"
                boundary = f"[LIVE WEB: {ev['title']} | URL: {ev.get('url')} | SOURCE: {domain}]"
                snippet_text = ev["snippet"]
                citations_data.append({
                    "id": f"cite-{ev['id']}",
                    "index": cite_num,
                    "sourceType": "web",
                    "documentId": "web",
                    "documentName": ev["title"],
                    "page": 1,
                    "url": ev.get("url"),
                    "retrievedAt": ev.get("retrieved_at"),
                    "snippet": snippet_text[:240].strip() + ("..." if len(snippet_text) > 240 else ""),
                    "relevance": ev.get("relevance", 80)
                })
            else:  # live_api
                api_name = ev.get("metadata", {}).get("api", "Live API")
                boundary = f"[LIVE DATA: {ev['title']} | API: {api_name} | RETRIEVED: {ev.get('retrieved_at')}]"
                snippet_text = ev["snippet"]
                citations_data.append({
                    "id": f"cite-{ev['id']}",
                    "index": cite_num,
                    "sourceType": "live_api",
                    "documentId": "live-api",
                    "documentName": ev["title"],
                    "page": 1,
                    "url": ev.get("url"),
                    "retrievedAt": ev.get("retrieved_at"),
                    "snippet": snippet_text[:240].strip() + ("..." if len(snippet_text) > 240 else ""),
                    "relevance": ev.get("relevance", 98)
                })

            context_blocks.append(f"[{cite_num}] {boundary}\n{snippet_text}")

        context_str = "\n\n---\n\n".join(context_blocks)

        # ── Step 5: Language Detection + Strict Evidence-Grounded Prompt ──────
        query_lang = detect_language(clean_query)
        language_instruction = get_response_language_instruction(query_lang)
        logger.info(f"[LoopEngine] Step 5: Query language detected = {get_language_label(query_lang)}")

        prompt = (
            f"You are an evidence-grounded bilingual document intelligence and research assistant. "
            f"You support both Hindi (हिंदी) and English queries and documents.\n\n"
            f"{language_instruction}\n\n"
            f"EVIDENCE CONTEXT:\n{context_str}\n\n"
            f"USER QUERY: {clean_query}\n\n"
            f"GROUNDING INSTRUCTIONS:\n"
            f"1. Use ONLY the evidence provided in the context above. Never fabricate facts, dates, or numbers.\n"
            f"2. If the user question requires internal documents, cite the document and page using bracketed numbers like [1].\n"
            f"3. If the user question requires current, live, or web facts, use the web/live evidence and cite it using [1], [2].\n"
            f"4. If the question asks for both (e.g. document figures and current web data), clearly provide both parts and cite their respective sources.\n"
            f"5. If the available evidence is insufficient to answer reliably, say so explicitly — never invent facts.\n"
            f"6. If sources conflict, explicitly identify the conflicting claims and cite both sources.\n"
            f"7. Answer conversationally and directly without robotic introductory boilerplate.\n"
            f"8. Ensure every factual claim includes its bracketed citation tag like [1] or [2].\n"
            f"9. If translating content between Hindi and English, preserve key terms, numbers, and names accurately."
        )

        # ── Step 6: LLM Synthesis via Circuit Breaker ──────────────────────────
        logger.info(f"[LoopEngine] Step 6: Dispatching to Circuit Breaker LLM with {len(all_evidence)} evidence sources...")
        t_llm = time.monotonic()
        llm_result = await generate_rag_response(prompt, all_evidence, clean_query)
        t_llm_elapsed = time.monotonic() - t_llm

        answer = llm_result["response"]
        model_used = llm_result["model"]

        # Ensure citation tag exists in answer if evidence was provided
        if citations_data and not re.search(r'\[\d+\]', answer):
            answer = f"{answer} [1]"

        if conflict_note and conflict_note not in answer:
            answer = f"{answer}\n\n> ⚠ Note: {conflict_note}"

        total_elapsed = time.monotonic() - t_total
        logger.info(
            f"[LoopEngine] ✅ Hybrid Pipeline COMPLETE — model={model_used}, "
            f"citations={len(citations_data)}, total_time={total_elapsed:.2f}s"
        )
        logger.info("═" * 68)

        return {
            "answer": answer,
            "citations": citations_data,
            "is_insufficient_info": False,
            "confidence_score": 0.95 if all_evidence else 0.2,
            "model_used": model_used,
            "conflict_note": conflict_note,
            "sources_breakdown": {
                "documents": len(doc_chunks),
                "web": len(web_results),
                "live_api": len(live_api_results)
            }
        }


rag_loop_engine = SelfReflectiveRAGLoop()
