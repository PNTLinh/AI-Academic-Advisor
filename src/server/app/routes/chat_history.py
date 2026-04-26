"""Chat history endpoints for logged-in users."""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..dependencies import get_academic_tools

router = APIRouter()


class MessageItem(BaseModel):
    id: str
    type: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class ChatSession(BaseModel):
    id: str
    title: str
    messages: List[MessageItem]
    created_at: str
    updated_at: str


@router.post("/chat-history")
def save_chat_message(
    session_id: str,
    message: MessageItem,
    x_user_id: str = Header(None),
    tools=Depends(get_academic_tools)
):
    """Lưu tin nhắn chat vào database (chỉ cho user đã login)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Chưa xác thực")
    
    try:
        # Get student_id from user_id
        student = tools.db.execute(
            "SELECT student_id FROM Students WHERE user_id = ?",
            (x_user_id,),
            fetchall=False
        )
        if not student:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ học sinh")
        
        student_id = student["student_id"]
        
        # Save to database
        tools.db.execute_write(
            """INSERT INTO chat_messages 
               (student_id, session_id, message_type, content, created_at) 
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (student_id, session_id, message.type, message.content)
        )
        
        # Update session timestamp
        tools.db.execute_write(
            "UPDATE chat_sessions SET updated_at = datetime('now') WHERE student_id = ? AND session_id = ?",
            (student_id, session_id)
        )
        
        return {"status": "success", "message_id": message.id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không thể lưu tin nhắn")


@router.get("/chat-history", response_model=List[ChatSession])
def get_chat_history(
    x_user_id: str = Header(None),
    tools=Depends(get_academic_tools)
):
    """Lấy toàn bộ lịch sử chat (chỉ cho user đã login)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Chưa xác thực")
    
    try:
        # Get student_id from user_id
        student = tools.db.execute(
            "SELECT student_id FROM Students WHERE user_id = ?",
            (x_user_id,),
            fetchall=False
        )
        if not student:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ học sinh")
        
        student_id = student["student_id"]
        
        # Get all sessions for this student
        sessions = tools.db.execute(
            """SELECT * FROM chat_sessions 
               WHERE student_id = ? 
               ORDER BY updated_at DESC""",
            (student_id,),
            fetchall=True
        )
        
        result = []
        for session in sessions:
            # Get messages for this session
            messages = tools.db.execute(
                """SELECT id, message_type, content, created_at FROM chat_messages 
                   WHERE student_id = ? AND session_id = ?
                   ORDER BY created_at ASC""",
                (student_id, session["session_id"]),
                fetchall=True
            )
            
            result.append({
                "id": session["session_id"],
                "title": session["title"],
                "messages": [
                    {
                        "id": m["id"],
                        "type": m["message_type"],
                        "content": m["content"],
                        "timestamp": m["created_at"]
                    }
                    for m in messages
                ],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"]
            })
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không thể tải lịch sử chat")


@router.post("/chat-session")
def create_chat_session(
    title: str,
    x_user_id: str = Header(None),
    tools=Depends(get_academic_tools)
):
    """Tạo session chat mới (chỉ cho user đã login)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Chưa xác thực")
    
    try:
        session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
        
        tools.db.execute_write(
            """INSERT INTO chat_sessions 
               (id, user_id, title, created_at, updated_at) 
               VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
            (session_id, x_user_id, title)
        )
        
        return {"session_id": session_id, "title": title}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không thể tạo session")


@router.delete("/chat-session/{session_id}")
def delete_chat_session(
    session_id: str,
    x_user_id: str = Header(None),
    tools=Depends(get_academic_tools)
):
    """Xóa một session chat (chỉ cho user đã login)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Chưa xác thực")
    
    try:
        # Verify ownership
        session = tools.db.execute(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, x_user_id),
            fetchall=False
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session không tồn tại")
        
        # Delete messages first
        tools.db.execute_write(
            "DELETE FROM chat_messages WHERE session_id = ?",
            (session_id,)
        )
        
        # Delete session
        tools.db.execute_write(
            "DELETE FROM chat_sessions WHERE id = ?",
            (session_id,)
        )
        
        return {"status": "success"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Không thể xóa session")
