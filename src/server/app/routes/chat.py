"""Chat router (agent-first).

Endpoints provided:
- POST /chat : agentic chat with memory per user
- POST /upload : file upload (pdf/png/jpg) saved to data/uploads/

This router builds a single formatted conversation string and calls
`run_agent_loop(client, formatted_input)`; it does NOT call tools
directly.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from ..mock_data.examples import CHAT_MOCK_RESPONSE
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging
import os
import time

# Agent import is performed lazily inside the handler to avoid importing
# agent modules at import-time (which may fail if agent package is incomplete).

logger = logging.getLogger(__name__)

# Agent chat router
router = APIRouter()

# Simple in-memory conversation memory: {user_id: [ {role, content}, ... ] }
memory: Dict[str, List[Dict[str, str]]] = {}


from ..models.schemas import ChatRequest, ChatResponse

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, x_user_id: Optional[str] = Header(None)):
    """Agentic chat endpoint.

    - Reads `X-User-Id` header if provided; otherwise uses "anonymous".
    - Maintains in-memory `memory[user_id]` (last 10 messages).
    - Formats conversation and calls `run_agent_loop(client, formatted_input)`.
    """
    user_id = x_user_id or "anonymous"
    logger.info(f"📨 Chat request from user: {user_id}")
    logger.info(f"   Message: {request.message}")
    
    response_text = "Xin lỗi, hệ thống chat đang gặp sự cố kết nối. Bạn hãy kiểm tra lại Server nhé."
    debug_info = None
    
    try:
        # 1. Update memory
        user_msgs = memory.setdefault(user_id, [])
        user_msgs.append({"role": "user", "content": request.message})
        if len(user_msgs) > 10: memory[user_id] = user_msgs[-10:]
        logger.debug(f"   Memory now has {len(user_msgs)} messages")

        # 2. Prepare conversation string
        formatted_input = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in user_msgs])
        logger.debug(f"   Formatted input ({len(formatted_input)} chars)")

        # 3. Try to get AI response, fallback to Mock if fails
        try:
            from src.agent.agent import create_agent, run_agent_loop
            logger.info(f"🤖 Calling agent...")
            client = create_agent()
            response_text = run_agent_loop(client, formatted_input, max_turns=request.max_turns)
            logger.info(f"✅ Agent returned ({len(response_text)} chars): {response_text[:100]}")
        except Exception as e:
            debug_info = str(e)
            logger.warning(f"⚠️  AGENT ERROR: {debug_info}. Falling back to Mock response.")
            response_text = CHAT_MOCK_RESPONSE["reply"]
            logger.info(f"   Using mock response ({len(response_text)} chars)")

        # 4. Record and return
        user_msgs.append({"role": "assistant", "content": response_text})
        logger.info(f"📤 Returning response to user")
        return ChatResponse(reply=response_text, debug_info=debug_info)
        
    except Exception as e:
        logger.exception("🔴 CRITICAL CHAT ERROR")
        return ChatResponse(reply=response_text, debug_info=str(e))


@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    """Accept file uploads; save to data/uploads/ and return saved path.

    Allowed extensions: .pdf, .png, .jpg
    """
    try:
        filename = file.filename or "upload"
        _, ext = os.path.splitext(filename.lower())
        allowed = {".pdf", ".png", ".jpg"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        # Make filename unique
        ts = int(time.time() * 1000)
        safe_name = f"{ts}_{os.path.basename(filename)}"
        dest_path = os.path.join(uploads_dir, safe_name)

        with open(dest_path, "wb") as f:
            content = file.file.read()
            f.write(content)

        return JSONResponse(content={"file_path": dest_path})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("File upload error")
        raise HTTPException(status_code=500, detail=str(e))
