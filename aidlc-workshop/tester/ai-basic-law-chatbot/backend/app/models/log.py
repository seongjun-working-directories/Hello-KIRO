from sqlalchemy import Column, Integer, String, Text
from app.database import Base
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    session_id     = Column(String(100), nullable=False, index=True)
    first_question = Column(Text, nullable=False)   # 첫 번째 사용자 질문
    messages       = Column(Text, nullable=False)   # 전체 대화 JSON
    created_at     = Column(String(30), nullable=False, default=_now)
