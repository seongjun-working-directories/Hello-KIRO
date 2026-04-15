import json
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limiter import check_rate_limit
from app.schemas.chat import ChatRequest, ChatMessage
from app.services.rag_service import RAGService
from app.services.openai_service import OpenAIService
from app.models.log import ConversationLog

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])
openai_service = OpenAIService()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class SaveLogRequest(BaseModel):
    session_id: str
    messages: List[ChatMessage]


@router.post("/chat/log", summary="대화 로그 저장")
def save_log(request: SaveLogRequest, db: Session = Depends(get_db)):
    try:
        first_question = next(
            (m.content for m in request.messages if m.role == "user"),
            "알 수 없음"
        )
        messages_data = [{"role": m.role, "content": m.content} for m in request.messages]
        existing = db.query(ConversationLog).filter(
            ConversationLog.session_id == request.session_id
        ).first()
        messages_json = json.dumps(messages_data, ensure_ascii=False)
        if existing:
            existing.messages = messages_json
        else:
            db.add(ConversationLog(
                session_id=request.session_id,
                first_question=first_question,
                messages=messages_json,
                created_at=datetime.now(timezone.utc).isoformat(),
            ))
        db.commit()
        logger.info("로그 저장 완료: session_id=%s", request.session_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error("로그 저장 실패: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="로그 저장 실패")


@router.post("/chat", summary="AI 기본법 준수 분석 (SSE 스트리밍)")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(check_rate_limit),
):
    if len(request.message) > 5000:
        raise HTTPException(
            status_code=400,
            detail={"detail": "입력이 5,000자를 초과했습니다.", "error_code": "INPUT_TOO_LONG"},
        )

    rag = RAGService(db)
    articles, guidelines = await rag.search_relevant_articles(request.message)
    context = rag.build_context(articles, guidelines)
    system_prompt = rag.build_system_prompt(context)
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]

    async def event_stream():
        full_response = ""
        try:
            async for chunk in openai_service.stream_chat(system_prompt, history_dicts, request.message):
                full_response += chunk
                yield _sse({"type": "chunk", "content": chunk})
            yield _sse({"type": "done", "content": full_response})
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield _sse({"type": "error", "message": "OpenAI API 연결에 실패했습니다. 잠시 후 다시 시도해주세요."})
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
