from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db, engine, Base
from ..models.message import Message
import json

router = APIRouter()

# Ensure tables exist (already called in chat, but safe)
Base.metadata.create_all(bind=engine)

@router.get("/sessions/{session_id}/messages", response_model=dict)
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    # Verify session exists
    msgs = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id).all()
    if not msgs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    result = []
    for msg in msgs:
        entry = {"role": msg.role, "content": msg.content}
        if msg.role == "assistant" and msg.message_metadata:
            try:
                entry["metadata"] = json.loads(msg.metadata)
            except Exception:
                entry["metadata"] = msg.metadata
        result.append(entry)
    return JSONResponse(content={"session_id": session_id, "messages": result})
