import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import chat, admin
import app.models.log  # noqa: F401 - register ConversationLog model

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI 기본법 준수 확인 챗봇",
    version="1.0.0",
    description="""
## AI 기본법 준수 확인 챗봇 API

한국 AI 기본법 준수 여부를 분석하는 챗봇 서비스의 백엔드 API입니다.

### 주요 기능
- **AI 기본법 준수 분석**: 사용자의 AI 프로젝트 아이디어를 GPT-4o mini로 분석
- **SSE 스트리밍**: 실시간 스트리밍 응답
- **PDF 내보내기**: 분석 결과를 PDF로 다운로드
- **Rate Limiting**: IP 기반 슬라이딩 윈도우 (10분/5회)

### 인증
- 일반 API: 인증 불필요 (완전 익명 서비스)
- 관리자 API (`/admin/*`): `X-Admin-Key` 헤더 필요
""",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/admin")


@app.get("/health")
def health_check():
    return {"status": "ok"}
