import json
import uuid
import asyncio
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.db.sqlite_cache import (
    get_all_chunks,
    get_cached_query,
    set_cached_query,
    hash_query,
    save_chat_message,
    get_chat_history,
    create_chat_session,
    get_all_chat_sessions,
    delete_chat_session
)
from app.rag.loop_engine import rag_loop_engine

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])
logger = logging.getLogger("DocuMind.ChatRouter")

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"
    document_context: Optional[str] = None
    stream: Optional[bool] = False

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat Session"

class QueryResponse(BaseModel):
    id: str
    role: str = "assistant"
    content: str
    citations: List[Dict[str, Any]] = []
    is_insufficient_info: bool = False
    model_used: str
    session_id: str
    conflict_note: Optional[str] = None

async def event_generator_for_query(
    query_text: str,
    session_id: str,
    doc_filter: Optional[str]
) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events (SSE) streaming generator:
    Streams response token-by-token or in conversational deltas,
    followed by evidence citations and final telemetry metadata.
    """
    user_msg_id = f"msg-u-{uuid.uuid4().hex[:6]}"
    await save_chat_message(
        msg_id=user_msg_id,
        session_id=session_id,
        role="user",
        content=query_text
    )

    # Check cache first
    q_hash = hash_query(query_text, doc_filter)
    cached = await get_cached_query(q_hash)
    
    if cached:
        full_text = cached["response"]
        citations = cached["citations"]
        model = f"{cached['model_used']} (Cached)"
    else:
        all_chunks = await get_all_chunks()
        rag_res = await rag_loop_engine.execute_rag_pipeline(
            query=query_text,
            all_chunks=all_chunks,
            doc_filter=doc_filter
        )
        full_text = rag_res["answer"]
        citations = rag_res["citations"]
        model = rag_res["model_used"]

        if not rag_res.get("is_insufficient_info", False):
            await set_cached_query(
                query_hash=q_hash,
                query_text=query_text,
                response=full_text,
                citations=citations,
                model_used=model
            )

    resp_id = f"msg-a-{uuid.uuid4().hex[:6]}"
    await save_chat_message(
        msg_id=resp_id,
        session_id=session_id,
        role="assistant",
        content=full_text,
        sources=citations
    )

    # 1. Stream token deltas
    words = full_text.split(" ")
    for idx, word in enumerate(words):
        delta = word + (" " if idx < len(words) - 1 else "")
        yield f"event: token\ndata: {json.dumps({'token': delta})}\n\n"
        await asyncio.sleep(0.02)  # Emulate smooth realistic streaming pace

    # 2. Stream citations event
    yield f"event: citations\ndata: {json.dumps({'citations': citations})}\n\n"

    # 3. Stream done event
    yield f"event: done\ndata: {json.dumps({'id': resp_id, 'model': model, 'session_id': session_id})}\n\n"

@router.post("/query")
async def query_rag(request: QueryRequest):
    """
    Core RAG Gateway endpoint:
    - If `stream=true`: Returns SSE text/event-stream
    - If `stream=false`: Returns standard JSON QueryResponse
    """
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    session_id = request.session_id or "default"

    # SSE Streaming mode
    if request.stream:
        return StreamingResponse(
            event_generator_for_query(user_query, session_id, request.document_context),
            media_type="text/event-stream"
        )

    user_msg_id = f"msg-u-{uuid.uuid4().hex[:6]}"
    await save_chat_message(
        msg_id=user_msg_id,
        session_id=session_id,
        role="user",
        content=user_query
    )

    # 1. Check Query Cache
    q_hash = hash_query(user_query, request.document_context)
    cached = await get_cached_query(q_hash)
    if cached:
        logger.info(f"Query cache HIT for query: '{user_query}'")
        resp_id = f"msg-a-{uuid.uuid4().hex[:6]}"
        await save_chat_message(
            msg_id=resp_id,
            session_id=session_id,
            role="assistant",
            content=cached["response"],
            sources=cached["citations"],
            is_insufficient=False
        )
        return QueryResponse(
            id=resp_id,
            content=cached["response"],
            citations=cached["citations"],
            is_insufficient_info=False,
            model_used=f"{cached['model_used']} (Cached)",
            session_id=session_id
        )

    # 2. Retrieve All Active Chunks from SQLite
    all_chunks = await get_all_chunks()

    # 3. Execute Self-Reflective Corrective RAG Loop
    result = await rag_loop_engine.execute_rag_pipeline(
        query=user_query,
        all_chunks=all_chunks,
        doc_filter=request.document_context
    )

    resp_id = f"msg-a-{uuid.uuid4().hex[:6]}"
    answer_text = result["answer"]
    citations = result["citations"]
    is_insufficient = result["is_insufficient_info"]
    model_name = result["model_used"]
    conflict_note = result.get("conflict_note")

    # 4. Save to chat history & cache
    await save_chat_message(
        msg_id=resp_id,
        session_id=session_id,
        role="assistant",
        content=answer_text,
        sources=citations,
        is_insufficient=is_insufficient
    )

    if not is_insufficient:
        await set_cached_query(
            query_hash=q_hash,
            query_text=user_query,
            response=answer_text,
            citations=citations,
            model_used=model_name
        )

    return QueryResponse(
        id=resp_id,
        content=answer_text,
        citations=citations,
        is_insufficient_info=is_insufficient,
        model_used=model_name,
        session_id=session_id,
        conflict_note=conflict_note
    )

@router.get("/stream")
async def stream_query_endpoint(
    query: str,
    session_id: str = "default",
    document_context: Optional[str] = None
):
    """Dedicated GET SSE endpoint for streaming responses to EventSource clients."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return StreamingResponse(
        event_generator_for_query(query.strip(), session_id, document_context),
        media_type="text/event-stream"
    )

# --- Sessions & History ---
@router.get("/history")
async def get_history(session_id: str = "default"):
    """Fetches full persistent chat history for an offline or active session."""
    history = await get_chat_history(session_id)
    return history

@router.get("/sessions")
async def list_sessions():
    """Lists all stored chat sessions."""
    return await get_all_chat_sessions()

@router.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """Creates a new conversation session."""
    sess_id = f"sess-{uuid.uuid4().hex[:8]}"
    return await create_chat_session(sess_id, request.title or "New Chat Session")

@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    """Deletes a session and associated messages."""
    await delete_chat_session(session_id)
    return {"status": "deleted", "session_id": session_id}
