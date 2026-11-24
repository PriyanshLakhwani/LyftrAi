from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from ..database import get_db, engine, Base
from ..models.message import Message
from ..schemas.chat import ChatRequest, ChatResponse, ChatResponseMetadata
from ..services.llm_service import LLMService
from ..services.llm_service import parse_failure_header
import json

router = APIRouter()

# Ensure tables exist
Base.metadata.create_all(bind=engine)

llm_service = LLMService()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db), x_simulate_failure: str = Header(None)):
    # Validate request (pydantic already does)
    session_id = request.session_id
    user_message = request.message.strip()
    system_prompt = request.system_prompt
    # Fetch previous messages for this session
    history = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id).all()
    # Build messages list for LLM (excluding system prompt which is handled separately)
    llm_messages = []
    for msg in history:
        role = "assistant" if msg.role == "assistant" else "user"
        llm_messages.append({"role": role, "content": msg.content})
    # Append current user message
    llm_messages.append({"role": "user", "content": user_message})
    # Call LLM service
    try:
        result = llm_service.get_response(llm_messages, system_prompt, x_simulate_failure)
    except Exception as e:
        # If all providers failed, raise 503
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="all providers unavailable")
    # Determine resolution source
    resolution_source = "LIVE_INFERENCE" if not result.get("from_cache", False) else "LLM_CACHE"
    # Store user message
    user_msg_obj = Message(session_id=session_id, role="user", content=user_message)
    db.add(user_msg_obj)
    db.flush()  # get id
    # Store assistant response with metadata
    metadata = {
        "resolution_source": resolution_source,
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "key_id": result.get("key_id"),
        "fallback_attempts": result.get("fallback_attempts", 0),
    }
    assistant_msg_obj = Message(
        session_id=session_id,
        role="assistant",
        content=result["reply"],
        message_metadata=json.dumps(metadata),
    )
    db.add(assistant_msg_obj)
    db.commit()
    # Build response
    resp_metadata = ChatResponseMetadata(
        resolution_source=resolution_source,
        model=result["model"],
        latency_ms=result["latency_ms"],
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
        key_id=result.get("key_id"),
        fallback_attempts=result.get("fallback_attempts", 0),
    )
    return ChatResponse(session_id=session_id, reply=result["reply"], metadata=resp_metadata)
