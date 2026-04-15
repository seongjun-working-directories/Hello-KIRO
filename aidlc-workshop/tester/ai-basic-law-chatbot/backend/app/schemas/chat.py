from pydantic import BaseModel, Field
from typing import Annotated, List, Optional, Literal
from datetime import datetime


class ComplianceItem(BaseModel):
    article_no: str
    title: str
    status: Literal["Compliant", "Partially Compliant", "Non-Compliant"]
    priority: Literal["높음", "중간", "낮음"]
    recommendation: Optional[str] = None
    article_summary: Optional[str] = None


class ComplianceData(BaseModel):
    overall: Literal["Compliant", "Partially Compliant", "Non-Compliant"]
    items: List[ComplianceItem]
    disclaimer: str = (
        "본 결과는 참고용이며, 법적 효력이 없습니다. "
        "정확한 법률 해석은 전문가에게 문의하세요."
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None
    compliance_data: Optional[ComplianceData] = None


class ChatRequest(BaseModel):
    message: str = Field(...)
    session_id: str = Field(..., min_length=1, max_length=100)
    history: Annotated[List[ChatMessage], Field(max_length=40)] = []


class ExportRequest(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    project_summary: str = Field(..., max_length=500)
