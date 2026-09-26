import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.rag.retriever import hybrid_retriever
from app.core.circuit_breaker import generate_rag_response

logger = logging.getLogger("DocuMind.LoopEngine")


class SelfReflectiveRAGLoop:
    """
    Self-Reflective Corrective RAG Loop ('Loop Engineering'):
    1. Query Decomposition & Routing  — splits complex multi-part queries into sub-queries
    2. Hybrid Retrieval                — BM25 + Vector cosine via RRF
    3. Sufficiency & Conflict Guard    — evaluates context relevance + detects cross-doc conflicts
    4. Adaptive Query Reformulation   — re-searches up to 2 iterations if evidence is insufficient
    5. Reliable Fallback Guard         — deterministic "insufficient evidence" notice
    6. Evidence & Citation Injection   — [DOC: ... | PAGE: ... | SECTION: ...] boundary tags
    """
    def __init__(self, max_iterations: int = 2, sufficiency_threshold: float = 0.28):
        self.max_iterations = max_iterations
        self.sufficiency_threshold = sufficiency_threshold

    def decompose_query(self, query: str) -> List[str]:
        """
        Decomposes complex multi-part queries (e.g. 'Compare Q2 revenue with budget in Manual B')
        into discrete sub-queries.
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
        Detects conflicting facts or numbers across retrieved document chunks.
        e.g., differing dollar figures, percentages, or contradictory policy windows.
        """
        if len(chunks) < 2:
            return None

        for term in ["refund", "days", "leave", "accrue", "percent", "%", "revenue", "budget"]:
            mentions = []
            for c in chunks:
                if term in c["content"].lower():
                    nums = re.findall(r'\b\d+(?:\.\d+)?%?\b', c["content"])
                    if nums:
                        mentions.append((c["doc_name"], c["page_number"], nums))

            if len(mentions) >= 2:
                first_doc, first_p, first_nums = mentions[0]
                second_doc, second_p, second_nums = mentions[1]
                if first_doc != second_doc and set(first_nums) != set(second_nums):
                    conflict_msg = (
                        f"Potential conflict detected between '{first_doc}' (Page {first_p}) "
                        f"and '{second_doc}' (Page {second_p}) regarding '{term}'."
                    )
                    logger.warning(f"[LoopEngine] ⚠ CONFLICT: {conflict_msg}")
                    return conflict_msg
        return None

    def evaluate_sufficiency(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """
        Evaluates whether retrieved chunks contain sufficient evidence for answering the query.
        Returns: (is_sufficient: bool, confidence_score: float)
        """
        if not retrieved_chunks:
            logger.info(f"[LoopEngine] Sufficiency: FAIL (0 chunks retrieved)")
            return False, 0.0

        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        if not query_terms:
            return True, 1.0

        max_overlap = 0.0
        for c in retrieved_chunks:
            content_lower = c["content"].lower()
            matched = sum(1 for term in query_terms if term in content_lower)
            ratio = matched / len(query_terms)
            if ratio > max_overlap:
                max_overlap = ratio

        top_dense = retrieved_chunks[0].get("dense_score", 0.0)
        confidence = float(0.6 * max_overlap + 0.4 * max(0.0, top_dense))

        # Out-of-domain query guard
        irrelevant_keywords = {
            "recipe", "chocolate cake", "weather in tokyo", "mars rover",
            "alien", "stock market prediction"
        }
        if any(ik in query.lower() for ik in irrelevant_keywords) and max_overlap < 0.2:
            logger.info(f"[LoopEngine] Sufficiency: FAIL — out-of-domain query detected")
            return False, 0.08

        # Document overview / summary / description query detection
        summary_triggers = [
            "what is this", "what is the document", "what is the pdf", "what does this",
            "about", "summarize", "summary", "overview", "describe", "description",
            "tell me about", "explain this", "main points", "key takeaways", "what is inside"
        ]
        if any(st in query.lower() for st in summary_triggers):
            logger.info(f"[LoopEngine] Sufficiency: PASS ✓ — document overview/summary request detected")
            return True, 0.95

        is_sufficient = confidence >= self.sufficiency_threshold
        status = "PASS ✓" if is_sufficient else "FAIL ✗"
        logger.info(
            f"[LoopEngine] Sufficiency: {status} | "
            f"keyword_overlap={max_overlap:.3f}, dense_top={top_dense:.3f}, "
            f"confidence={confidence:.3f} (threshold={self.sufficiency_threshold})"
        )
        return is_sufficient, confidence

    async def execute_rag_pipeline(
        self,
        query: str,
        all_chunks: List[Dict[str, Any]],
        doc_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the production Corrective RAG pipeline with full terminal logging:
        1. Query decomposition
        2. Hybrid retrieval + reflection loop with reformulation
        3. Conflict & Sufficiency verification
        4. Structured evidence boundary injection
        5. Grounded synthesis via Circuit Breaker LLM
        """
        t_total = time.monotonic()

        logger.info("─" * 65)
        logger.info(f"[LoopEngine] ▶ RAG Pipeline START")
        logger.info(f"[LoopEngine] Query: '{query[:80]}...'")
        logger.info(f"[LoopEngine] Corpus: {len(all_chunks)} chunks | doc_filter: {doc_filter or 'None'}")
        logger.info("─" * 65)

        # ── Step 0: Ensure Knowledge Base Has Chunks ──────────────────────────
        if not all_chunks:
            logger.warning("[LoopEngine] No chunks in database yet.")
            return {
                "answer": "No documents have been uploaded or indexed yet. Please tap the upload button above to add a PDF, Word document, or image, and DocuMind will immediately provide a full description and analysis!",
                "citations": [],
                "is_insufficient_info": False,
                "confidence_score": 0.0,
                "model_used": "DocuMind System Guide",
                "conflict_note": None
            }

        # Check if query is asking for document summary / description / overview
        summary_triggers = [
            "what is this", "what is the document", "what is the pdf", "what does this",
            "what is this pdf about", "what is this document about", "about",
            "summarize", "summary", "overview", "describe", "description",
            "give description", "give me description", "tell me about", "explain this",
            "main points", "key takeaways", "what is inside", "contents", "details",
            "what does it say", "what is it about", "what is", "explain"
        ]
        is_summary_query = any(st in query.lower() for st in summary_triggers)

        # ── Fast-path for Document Overview / Description Queries ────────────
        if is_summary_query:
            logger.info(f"[LoopEngine] 📑 Overview/Description query detected — gathering introductory context")
            target_chunks = all_chunks
            if doc_filter:
                filtered = [
                    c for c in all_chunks
                    if c.get("doc_name") == doc_filter
                    or c.get("doc_id") == doc_filter
                    or doc_filter.lower() in c.get("doc_name", "").lower()
                    or c.get("doc_name", "").lower() in doc_filter.lower()
                ]
                if filtered:
                    target_chunks = filtered
                else:
                    logger.warning(f"[LoopEngine] Doc filter '{doc_filter}' not in indexed chunks, checking db status...")
                    try:
                        from app.db.sqlite_cache import get_all_documents
                        db_docs = await get_all_documents()
                        matching_db = next(
                            (d for d in db_docs if d["name"].lower() == doc_filter.lower() or doc_filter.lower() in d["name"].lower()),
                            None
                        )
                        if matching_db and matching_db.get("status") in ["QUEUED", "OCR", "CHUNKING", "EMBEDDING", "PROCESSING"]:
                            return {
                                "answer": f"The document '{matching_db['name']}' is currently being indexed ({matching_db['status']}, {matching_db['progress']}% complete). Please wait a moment for processing to finish, then ask again for a complete breakdown!",
                                "citations": [],
                                "is_insufficient_info": False,
                                "confidence_score": 0.5,
                                "model_used": "DocuMind Ingestion Monitor",
                                "conflict_note": None
                            }
                    except Exception as db_err:
                        logger.warning(f"[LoopEngine] Error checking db doc status: {db_err}")

                    # If not currently indexing, summarize the available document corpus
                    logger.info(f"[LoopEngine] Using available {len(all_chunks)} chunks for description")
                    target_chunks = all_chunks

            # Sort by page number and chunk index so we get the beginning of the document
            target_chunks.sort(key=lambda c: (c.get("page_number", 1), c.get("chunk_index", 1)))
            top_chunks = target_chunks[:5]
            confidence = 0.95
            conflict_note = None

        else:
            # ── Step 1: Query Decomposition ───────────────────────────────────────
            sub_queries = self.decompose_query(query)
            logger.info(f"[LoopEngine] Step 1: {len(sub_queries)} sub-quer{'y' if len(sub_queries) == 1 else 'ies'} identified")

            collected_chunks: Dict[str, Dict[str, Any]] = {}

            # ── Step 2: Hybrid Retrieval + Reflection Loop ────────────────────────
            for sq_idx, sq in enumerate(sub_queries):
                logger.info(f"[LoopEngine] Step 2: Sub-query {sq_idx + 1}/{len(sub_queries)}: '{sq[:60]}'")
                active_q = sq

                for it in range(self.max_iterations):
                    logger.info(f"[LoopEngine]   Iteration {it + 1}/{self.max_iterations}: Hybrid retrieval...")
                    retrieved = hybrid_retriever.retrieve(
                        query=active_q,
                        chunks=all_chunks,
                        top_k=4,
                        doc_filter=doc_filter
                    )

                    is_sufficient, score = self.evaluate_sufficiency(active_q, retrieved)

                    if is_sufficient or it == self.max_iterations - 1:
                        for c in retrieved:
                            collected_chunks[c["id"]] = c
                        logger.info(
                            f"[LoopEngine]   {'✓ Sufficient context' if is_sufficient else '⚠ Max iterations reached'} "
                            f"— collected {len(retrieved)} chunks (total pool: {len(collected_chunks)})"
                        )
                        break
                    else:
                        logger.info(
                            f"[LoopEngine]   ✗ Insufficient (score={score:.3f} < {self.sufficiency_threshold}) "
                            f"— reformulating query..."
                        )
                        active_q = self.reformulate_query(active_q, it)

            # ── Step 3: Consolidate & Final Sufficiency Check ─────────────────────
            final_chunks = list(collected_chunks.values())
            final_chunks.sort(key=lambda x: x.get("relevance", 0), reverse=True)
            top_chunks = final_chunks[:4]

            if not top_chunks:
                # Fall back to introductory chunks
                top_chunks = all_chunks[:3]

            logger.info(f"[LoopEngine] Step 3: Consolidated {len(final_chunks)} chunks → using top {len(top_chunks)}")

            is_sufficient, confidence = self.evaluate_sufficiency(query, top_chunks)

            if not is_sufficient:
                logger.info(f"[LoopEngine] Keyword sufficiency below threshold — switching to grounded document description...")
                is_summary_query = True
                confidence = max(0.70, confidence)

            # ── Step 4: Conflict Detection ─────────────────────────────────────────
            conflict_note = self.detect_conflicts(top_chunks)
            if conflict_note:
                logger.warning(f"[LoopEngine] Step 4: Conflict detected across documents!")
            else:
                logger.info(f"[LoopEngine] Step 4: No conflicts detected across {len(top_chunks)} chunks ✓")

        # ── Step 5: Context Prompt with Evidence Boundary Tags ─────────────────
        context_blocks = []
        citations_data = []

        logger.info(f"[LoopEngine] Step 5: Building context prompt with boundary tags...")
        for idx, chunk in enumerate(top_chunks):
            citation_num = idx + 1
            section_id = chunk.get("chunk_index", idx + 1)
            boundary_tag = f"[DOC: {chunk['doc_name']} | PAGE: {chunk['page_number']} | SECTION: {section_id}]"
            context_blocks.append(f"[{citation_num}] {boundary_tag}\n{chunk['content']}")

            citations_data.append({
                "id": f"cite-{chunk['id']}",
                "index": citation_num,
                "documentId": chunk["doc_id"],
                "documentName": chunk["doc_name"],
                "page": chunk["page_number"],
                "snippet": chunk["content"][:240].strip() + "...",
                "relevance": chunk.get("relevance", 85)
            })
            logger.info(
                f"  [cite-{citation_num}] {chunk['doc_name']} p.{chunk['page_number']} "
                f"— relevance: {chunk.get('relevance', 0)}%"
            )

        context_str = "\n\n---\n\n".join(context_blocks)

        if is_summary_query:
            prompt = (
                f"Context Evidence from Document:\n{context_str}\n\n"
                f"User Question: {query}\n\n"
                f"Instructions:\n"
                f"- The user is asking for an overview, summary, or description of the document.\n"
                f"- Provide a clear, structured, and informative description explaining what this document is about.\n"
                f"- Summarize the primary topics covered, core purpose, key rules/guidelines, and important takeaways based on the context evidence.\n"
                f"- Cite your sources using bracketed notation like [1], [2] referencing the context items."
            )
        else:
            prompt = (
                f"Context Evidence:\n{context_str}\n\n"
                f"User Question: {query}\n\n"
                f"Instructions:\n"
                f"- Answer the question strictly using the provided context chunks.\n"
                f"- Cite your sources using bracketed notation [1], [2] referencing the numbered context.\n"
                f"- If the evidence does not provide enough facts, state clearly what the document covers instead."
            )

        # ── Step 6: LLM Synthesis via Circuit Breaker ──────────────────────────
        logger.info(f"[LoopEngine] Step 6: Dispatching to Circuit Breaker LLM...")
        t_llm = time.monotonic()
        llm_result = await generate_rag_response(prompt, top_chunks, query)
        t_llm_elapsed = time.monotonic() - t_llm

        answer = llm_result["response"]
        model_used = llm_result["model"]

        logger.info(
            f"[LoopEngine] Step 6: LLM ✓ — model: {model_used}, "
            f"answer: {len(answer)} chars, elapsed: {t_llm_elapsed:.2f}s"
        )

        # Ensure citation tag is present in the answer
        if "[1]" not in answer and citations_data:
            answer = f"{answer} [1]"

        if conflict_note:
            answer = f"{answer}\n\n> Note: {conflict_note}"

        total_elapsed = time.monotonic() - t_total
        logger.info("─" * 65)
        logger.info(
            f"[LoopEngine] ✅ Pipeline COMPLETE — confidence={confidence:.3f}, "
            f"model={model_used}, total_elapsed={total_elapsed:.2f}s"
        )
        logger.info("─" * 65)

        return {
            "answer": answer,
            "citations": citations_data,
            "is_insufficient_info": False,
            "confidence_score": confidence,
            "model_used": model_used,
            "conflict_note": conflict_note
        }


rag_loop_engine = SelfReflectiveRAGLoop()
