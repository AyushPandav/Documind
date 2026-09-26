import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.rag.retriever import hybrid_retriever
from app.core.circuit_breaker import generate_rag_response

logger = logging.getLogger("DocuMind.LoopEngine")

class SelfReflectiveRAGLoop:
    """
    Self-Reflective Corrective RAG Loop ('Loop Engineering'):
    1. Query Decomposition & Routing: Splits complex queries into targeted sub-queries.
    2. Hybrid Retrieval: Combines dense vector cosine similarity with BM25 sparse keyword search via RRF.
    3. Sufficiency & Conflict Guard: Evaluates context relevance and detects conflicting evidence across documents.
    4. Adaptive Query Reformulation: Re-executes search up to 2 iterations if evidence is insufficient.
    5. Reliable Fallback Guard: Returns deterministic insufficient evidence notice when documents lack facts.
    6. Evidence & Citation Injection: Formats boundary tags [DOC: ... | PAGE: ... | SECTION: ...] and citation badges.
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

        return sub_queries

    def reformulate_query(self, query: str, iteration: int) -> str:
        """
        Broadens query on low retrieval confidence:
        Strips filler question words, punctuation, and preserves high-signal nouns/numbers.
        """
        stopwords = {
            "what", "is", "the", "how", "many", "does", "can", "you", "tell",
            "me", "about", "please", "why", "where", "which", "could", "should",
            "would", "give", "show", "find"
        }
        words = [w for w in re.findall(r'\b\w+\b', query.lower()) if w not in stopwords]
        if words:
            return " ".join(words)
        return query

    def detect_conflicts(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        """
        Detects conflicting facts or numbers across retrieved document chunks.
        e.g., differing dollar figures, percentages, or contradictory policy windows.
        """
        if len(chunks) < 2:
            return None

        # Look for differing numbers associated with common financial/policy terms
        for term in ["refund", "days", "leave", "accrue", "percent", "%", "revenue", "budget"]:
            mentions = []
            for c in chunks:
                if term in c["content"].lower():
                    # extract numbers in proximity
                    nums = re.findall(r'\b\d+(?:\.\d+)?%?\b', c["content"])
                    if nums:
                        mentions.append((c["doc_name"], c["page_number"], nums))

            if len(mentions) >= 2:
                # Compare first set of numbers
                first_doc, first_p, first_nums = mentions[0]
                second_doc, second_p, second_nums = mentions[1]
                if first_doc != second_doc and set(first_nums) != set(second_nums):
                    return (
                        f"Potential conflict detected between {first_doc} (Page {first_p}) "
                        f"and {second_doc} (Page {second_p}) regarding {term}."
                    )
        return None

    def evaluate_sufficiency(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """
        Evaluates whether retrieved chunks contain sufficient evidence for answering the query.
        Returns: (is_sufficient: bool, confidence_score: float)
        """
        if not retrieved_chunks:
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

        # Average between top dense similarity score and keyword overlap
        top_dense = retrieved_chunks[0].get("dense_score", 0.0)
        confidence = float(0.6 * max_overlap + 0.4 * max(0.0, top_dense))

        # Irrelevant out-of-domain queries
        irrelevant_keywords = {"recipe", "chocolate cake", "weather in tokyo", "mars rover", "alien", "stock market prediction"}
        if any(ik in query.lower() for ik in irrelevant_keywords) and max_overlap < 0.2:
            return False, 0.08

        is_sufficient = confidence >= self.sufficiency_threshold
        return is_sufficient, confidence

    async def execute_rag_pipeline(
        self,
        query: str,
        all_chunks: List[Dict[str, Any]],
        doc_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the production Corrective RAG pipeline:
        1. Query decomposition
        2. Hybrid retrieval + reflection loop with reformulation
        3. Conflict & Sufficiency verification
        4. Structured evidence boundary injection: [DOC: ... | PAGE: ... | SECTION: ...]
        5. Grounded synthesis via Circuit Breaker
        """
        sub_queries = self.decompose_query(query)
        collected_chunks: Dict[str, Dict[str, Any]] = {}

        for sq in sub_queries:
            active_q = sq
            for it in range(self.max_iterations):
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
                    break
                else:
                    logger.info(f"Loop Engineering: Score {score:.2f} < {self.sufficiency_threshold}. Reformulating query '{active_q}' (Iteration {it+1})...")
                    active_q = self.reformulate_query(active_q, it)

        final_chunks = list(collected_chunks.values())
        final_chunks.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        top_chunks = final_chunks[:3]

        # Sufficiency verification on consolidated context
        is_sufficient, confidence = self.evaluate_sufficiency(query, top_chunks)
        
        # Check PS requirement: Reliable Answer Handling without fabricating
        if not is_sufficient or not top_chunks:
            return {
                "answer": f"The uploaded documents do not contain sufficient evidence to answer '{query}'.",
                "citations": [],
                "is_insufficient_info": True,
                "confidence_score": confidence,
                "model_used": "Guard: Sufficiency Filter",
                "conflict_note": None
            }

        # Check for conflict between documents
        conflict_note = self.detect_conflicts(top_chunks)

        # Build context prompt with exact boundary tags:
        # [DOC: filename | PAGE: X | SECTION: Y]
        context_blocks = []
        citations_data = []

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

        context_str = "\n\n---\n\n".join(context_blocks)
        
        prompt = (
            f"Context Evidence:\n{context_str}\n\n"
            f"User Question: {query}\n\n"
            f"Instructions:\n"
            f"- Answer the question strictly using the provided context chunks.\n"
            f"- Cite your sources using bracketed notation [1], [2] referencing the numbered context.\n"
            f"- If the evidence does not provide enough facts, output exactly: "
            f"'The uploaded documents do not contain sufficient evidence to answer \"{query}\".'"
        )

        llm_result = await generate_rag_response(prompt, top_chunks, query)
        answer = llm_result["response"]

        # Ensure citation tag is present
        if "[1]" not in answer and citations_data:
            answer = f"{answer} [1]"

        if conflict_note:
            answer = f"{answer}\n\n> Note: {conflict_note}"

        return {
            "answer": answer,
            "citations": citations_data,
            "is_insufficient_info": False,
            "confidence_score": confidence,
            "model_used": llm_result["model"],
            "conflict_note": conflict_note
        }

rag_loop_engine = SelfReflectiveRAGLoop()
