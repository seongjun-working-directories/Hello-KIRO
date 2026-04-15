# AI 기본법 준수 확인 챗봇 - 설계 문서 (Design Document)

## 1. 개요 (Overview)

본 서비스는 한국 AI 기본법 준수 여부를 확인해주는 웹 기반 챗봇이다.
사용자는 자신의 AI 프로젝트 아이디어를 자유 텍스트로 입력하고, 시스템은 Query Expansion → 임베딩 기반 벡터 검색 → GPT-4o mini 분석의 3단계 RAG 파이프라인으로 준수 여부를 분석한다.

### 핵심 특성
- 완전 익명 서비스 (회원가입/로그인 없음)
- 서버 무상태 설계 (세션 데이터는 프론트엔드 sessionStorage에만 보관)
- SSE(Server-Sent Events) 기반 스트리밍 응답
- IP 기반 Rate Limiting (인메모리 슬라이딩 윈도우)
- 면책 조항 필수 포함
- Query Expansion + 임베딩 벡터 검색 기반 고정확도 RAG

---

## 2. 아키텍처 (Architecture)

### 2.1 전체 시스템 컴포넌트 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  React + Vite + TypeScript                   │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │   │
│  │  │  ChatWindow  │  │  MessageList │  │  ExportButton     │   │   │
│  │  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘   │   │
│  │         │                │                    │              │   │
│  │  ┌──────▼────────────────▼────────────────────▼──────────┐   │   │
│  │  │              useChatSession (Custom Hook)              │   │   │
│  │  │         sessionStorage: messages[], sessionId          │   │   │
│  │  └──────────────────────────┬─────────────────────────────┘   │   │
│  └─────────────────────────────┼────────────────────────────────┘   │
│                                │ REST / SSE                          │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   FastAPI (Python)       │
                    │                         │
                    │  ┌───────────────────┐  │
                    │  │  Rate Limiter     │  │
                    │  │  (In-Memory Dict) │  │
                    │  └────────┬──────────┘  │
                    │           │             │
                    │  ┌────────▼──────────┐  │
                    │  │  Chat Router      │  │
                    │  │  POST /api/chat   │  │
                    │  │  (SSE Stream)     │  │
                    │  └────────┬──────────┘  │
                    │           │             │
                    │  ┌────────▼──────────┐  │
                    │  │  RAG Pipeline     │  │
                    │  │  - Query Expansion│  │
                    │  │  - 임베딩 검색    │  │
                    │  │  - 프롬프트 구성  │  │
                    │  └────┬──────┬───────┘  │
                    │       │      │           │
                    └───────┼──────┼───────────┘
                            │      │
               ┌────────────▼──┐  ┌▼──────────────────┐
               │  SQLite DB    │  │  OpenAI API        │
               │               │  │  GPT-4o mini       │
               │  articles     │  │  text-embedding    │
               │  paragraphs   │  │  -3-small          │
               │  subparagraphs│  │                    │
               │  items        │  │  - Query Expansion │
               │  embeddings   │  │  - 준수 분석       │
               └───────────────┘  │  - 스트리밍 응답   │
                                  │  - 법령 파싱       │
                                  └────────────────────┘
```

### 2.2 요청 흐름 (Request Flow)

```
[사용자 입력]
     │
     ▼
[프론트엔드: POST /api/chat]
     │
     ▼
[Rate Limiter 검사] ──── 초과 ────► [HTTP 429 반환]
     │ 통과
     ▼
[입력 검증: 5000자 초과?] ── 초과 ─► [HTTP 400 반환]
     │ 통과
     ▼
[Query Expansion: GPT로 법적 쟁점 키워드 추출]
     │
     ▼
[임베딩 검색: 질문+키워드 임베딩 → 코사인 유사도 → 상위 5개 조항]
     │ (임베딩 없으면 LIKE 검색으로 폴백)
     ▼
[GPT-4o mini 프롬프트 구성 (조항 컨텍스트 포함)]
     │
     ▼
[OpenAI API 호출 (스트리밍)]
     │
     ▼
[SSE 청크 단위 프론트엔드 전송]
     │
     ▼
[스트림 종료 이벤트 전송]
```

---

## 3. 디렉토리 구조 (Directory Structure)

```
ai-basic-law-chatbot/                    # 프로젝트 루트
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI 앱 진입점, 미들웨어 등록
│   │   ├── config.py                    # 환경변수 로드 (pydantic BaseSettings)
│   │   ├── database.py                  # SQLAlchemy 엔진, 세션 팩토리
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── law.py                   # SQLAlchemy ORM 모델 (Article 등)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                  # Pydantic 요청/응답 스키마
│   │   │   └── law.py                   # 법령 파싱 관련 스키마
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                  # POST /api/chat, POST /api/chat/export-pdf
│   │   │   └── admin.py                 # POST /admin/parse-law, POST /admin/embed-law
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rag_service.py           # RAG 파이프라인 (Query Expansion + 임베딩 검색 + 프롬프트)
│   │   │   ├── embedding_service.py     # OpenAI 임베딩 생성 및 벡터 검색
│   │   │   ├── openai_service.py        # OpenAI API 호출, 재시도 로직
│   │   │   ├── law_parser_service.py    # PDF 파싱 + GPT 구조화 파싱
│   │   │   └── pdf_export_service.py    # WeasyPrint PDF 생성
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── rate_limiter.py          # IP 기반 슬라이딩 윈도우 Rate Limiter
│   │   └── templates/
│   │       └── export_report.html       # Jinja2 PDF 내보내기 템플릿
│   ├── data/
│   │   ├── ai_basic_law.pdf             # AI 기본법 원문 PDF
│   │   └── fonts/
│   │       ├── KBFGDisplay-Light.ttf
│   │       ├── KBFGDisplay-Medium.ttf
│   │       ├── KBFGText-Bold.ttf
│   │       ├── KBFGText-Light.ttf
│   │       └── KBFGText-Medium.ttf
│   ├── migrations/
│   │   ├── env.py                       # Alembic 환경 설정
│   │   ├── script.py.mako
│   │   └── versions/                    # 마이그레이션 파일들
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_chat.py
│   │   ├── test_rate_limiter.py
│   │   ├── test_law_parser.py
│   │   ├── test_pdf_export.py
│   │   └── test_admin.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                     # React 진입점
│   │   ├── App.tsx                      # 루트 컴포넌트
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx           # 전체 채팅 레이아웃
│   │   │   ├── MessageList.tsx          # 메시지 목록 렌더링
│   │   │   ├── MessageBubble.tsx        # 개별 메시지 버블
│   │   │   ├── InputBar.tsx             # 텍스트 입력 + 전송 버튼
│   │   │   ├── ExportButton.tsx         # PDF 내보내기 버튼
│   │   │   ├── LoadingIndicator.tsx     # 스트리밍 중 로딩 표시
│   │   │   └── DisclaimerBanner.tsx     # 면책 조항 배너
│   │   ├── hooks/
│   │   │   ├── useChatSession.ts        # 세션 상태 관리 (sessionStorage)
│   │   │   └── useSSE.ts                # SSE 연결 및 스트리밍 처리
│   │   ├── api/
│   │   │   └── client.ts                # API 호출 함수 모음
│   │   ├── types/
│   │   │   └── index.ts                 # TypeScript 타입 정의
│   │   └── styles/
│   │       └── index.css                # Tailwind CSS 진입점 + @font-face 선언
│   ├── public/
│   │   └── fonts/
│   │       ├── KBFGDisplay-Light.ttf
│   │       ├── KBFGDisplay-Medium.ttf
│   │       ├── KBFGText-Bold.ttf
│   │       ├── KBFGText-Light.ttf
│   │       └── KBFGText-Medium.ttf
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── .env.example
│
└── README.md
```

---

## 4. REST API 엔드포인트 설계

### 4.1 POST /api/chat

챗봇 질문 전송 및 SSE 스트리밍 응답.

**Request**
```http
POST /api/chat
Content-Type: application/json

{
  "message": "저는 얼굴 인식 기반 출입 통제 시스템을 개발하려고 합니다...",
  "session_id": "sess_abc123",
  "history": [
    {
      "role": "user",
      "content": "이전 질문 내용"
    },
    {
      "role": "assistant",
      "content": "이전 응답 내용"
    }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | string | ✅ | 사용자 입력 (최대 5,000자) |
| session_id | string | ✅ | 프론트엔드 생성 세션 ID (UUID v4) |
| history | array | ✅ | 이전 대화 내역 (최대 20턴) |

**Response (SSE Stream)**
```
Content-Type: text/event-stream

data: {"type": "chunk", "content": "안녕하세요. 분석을 시작합니다."}

data: {"type": "chunk", "content": " 귀하의 프로젝트는..."}

data: {"type": "done", "compliance_summary": {"overall": "Partially Compliant", "items": [...]}}

data: [DONE]
```

**SSE 이벤트 타입**

| type | 설명 |
|------|------|
| chunk | 스트리밍 텍스트 청크 |
| done | 스트림 종료 + 최종 구조화 데이터 |
| error | 오류 발생 |

**HTTP 상태 코드**

| 코드 | 조건 |
|------|------|
| 200 | 정상 (SSE 스트림 시작) |
| 400 | 입력 검증 실패 (5000자 초과 등) |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |
| 503 | OpenAI API 연결 실패 |

---

### 4.2 POST /api/chat/export-pdf

대화 내용을 PDF로 내보내기.

**Request**
```http
POST /api/chat/export-pdf
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "messages": [
    {
      "role": "user",
      "content": "얼굴 인식 기반 출입 통제 시스템을 개발하려고 합니다.",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "분석 결과입니다...",
      "timestamp": "2025-01-15T10:30:15Z",
      "compliance_data": {
        "overall": "Partially Compliant",
        "items": [
          {
            "article_no": "제22조",
            "title": "고위험 AI 시스템 요건",
            "status": "Non-Compliant",
            "priority": "높음",
            "recommendation": "생체정보 처리에 대한 명시적 동의 절차 필요"
          }
        ]
      }
    }
  ],
  "project_summary": "얼굴 인식 기반 출입 통제 시스템"
}
```

**Response**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="compliance_report_20250115_103015.pdf"

[PDF binary data]
```

**HTTP 상태 코드**

| 코드 | 조건 |
|------|------|
| 200 | PDF 생성 성공 |
| 400 | 요청 데이터 누락 또는 형식 오류 |
| 500 | PDF 생성 실패 |

---

### 4.3 POST /admin/parse-law

AI 기본법 PDF 파싱 및 DB 저장 (관리자 전용).

**Request**
```http
POST /admin/parse-law
X-Admin-Key: your-secret-key-here
Content-Type: application/json

{}
```

**Response (성공)**
```json
{
  "status": "success",
  "message": "AI 기본법 파싱 및 저장 완료",
  "stats": {
    "articles": 42,
    "paragraphs": 187,
    "subparagraphs": 95,
    "items": 34,
    "total": 358
  },
  "processed_at": "2025-01-15T10:30:00Z"
}
```

**Response (인증 실패)**
```json
{
  "detail": "인증 실패: 유효하지 않은 관리자 키입니다."
}
```

**HTTP 상태 코드**

| 코드 | 조건 |
|------|------|
| 200 | 파싱 및 저장 성공 |
| 401 | X-Admin-Key 없음 또는 불일치 |
| 500 | 파싱 오류 또는 DB 저장 실패 |

---

## 5. SQLite DB 스키마

### 5.1 테이블 정의

#### articles (조)
```sql
CREATE TABLE articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_no  TEXT    NOT NULL,          -- "제1조", "제22조" 등
    title       TEXT    NOT NULL,          -- 조 제목
    content     TEXT,                      -- 조 본문 (항이 없는 경우)
    category    TEXT,                      -- 분류 (예: "고위험AI", "투명성" 등)
    effective_date TEXT,                   -- 시행일 (예: "2026-01-22")
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_articles_article_no ON articles(article_no);
CREATE INDEX idx_articles_category ON articles(category);
```

#### paragraphs (항)
```sql
CREATE TABLE paragraphs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id    INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    paragraph_no  TEXT    NOT NULL,        -- "①", "②" 등
    content       TEXT    NOT NULL,
    category      TEXT,
    effective_date TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_paragraphs_article_id ON paragraphs(article_id);
```

#### subparagraphs (호)
```sql
CREATE TABLE subparagraphs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    paragraph_id     INTEGER NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    subparagraph_no  TEXT    NOT NULL,     -- "1.", "2." 등
    content          TEXT    NOT NULL,
    category         TEXT,
    effective_date   TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_subparagraphs_paragraph_id ON subparagraphs(paragraph_id);
```

#### items (목)
```sql
CREATE TABLE items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    subparagraph_id  INTEGER NOT NULL REFERENCES subparagraphs(id) ON DELETE CASCADE,
    item_no          TEXT    NOT NULL,     -- "가.", "나." 등
    content          TEXT    NOT NULL,
    category         TEXT,
    effective_date   TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_items_subparagraph_id ON items(subparagraph_id);
```

### 5.2 ERD (ASCII)

```
┌─────────────────┐
│    articles     │
├─────────────────┤
│ id (PK)         │
│ article_no      │
│ title           │
│ content         │
│ category        │
│ effective_date  │
│ created_at      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐
│   paragraphs    │
├─────────────────┤
│ id (PK)         │
│ article_id (FK) │◄── articles.id
│ paragraph_no    │
│ content         │
│ category        │
│ effective_date  │
│ created_at      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐
│  subparagraphs  │
├─────────────────┤
│ id (PK)         │
│ paragraph_id(FK)│◄── paragraphs.id
│ subparagraph_no │
│ content         │
│ category        │
│ effective_date  │
│ created_at      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐
│     items       │
├─────────────────┤
│ id (PK)         │
│ subparagraph_id │◄── subparagraphs.id
│   (FK)          │
│ item_no         │
│ content         │
│ category        │
│ effective_date  │
│ created_at      │
└─────────────────┘
```

### 5.3 인덱스 전략

- `articles.article_no`: 조항 번호로 직접 조회 시 사용
- `articles.category`: 카테고리별 필터링 시 사용
- `paragraphs.article_id`, `subparagraphs.paragraph_id`, `items.subparagraph_id`: 계층 조회 JOIN 최적화

### 5.4 embeddings 테이블 (임베딩 벡터 저장)

```sql
CREATE TABLE embeddings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    vector      BLOB    NOT NULL,   -- numpy float32 배열을 bytes로 직렬화
    model       TEXT    NOT NULL DEFAULT 'text-embedding-3-small',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_embeddings_article_id ON embeddings(article_id);
```

각 article의 전체 텍스트(article_no + title + content + 모든 하위 항목 내용)를 하나의 문자열로 합쳐 임베딩한다.

---

## 6. 컴포넌트 및 인터페이스 (Components and Interfaces)

### 6.1 백엔드 컴포넌트

#### 6.1.1 SQLAlchemy ORM 모델 (`app/models/law.py`)

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class Article(Base):
    __tablename__ = "articles"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    article_no     = Column(String(20), nullable=False, index=True)
    title          = Column(Text, nullable=False)
    content        = Column(Text, nullable=True)
    category       = Column(String(100), nullable=True, index=True)
    effective_date = Column(String(20), nullable=True)
    created_at     = Column(String(30), nullable=False)

    paragraphs = relationship("Paragraph", back_populates="article",
                              cascade="all, delete-orphan")


class Paragraph(Base):
    __tablename__ = "paragraphs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    article_id     = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    paragraph_no   = Column(String(10), nullable=False)
    content        = Column(Text, nullable=False)
    category       = Column(String(100), nullable=True)
    effective_date = Column(String(20), nullable=True)
    created_at     = Column(String(30), nullable=False)

    article       = relationship("Article", back_populates="paragraphs")
    subparagraphs = relationship("Subparagraph", back_populates="paragraph",
                                 cascade="all, delete-orphan")


class Subparagraph(Base):
    __tablename__ = "subparagraphs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    paragraph_id     = Column(Integer, ForeignKey("paragraphs.id"), nullable=False, index=True)
    subparagraph_no  = Column(String(10), nullable=False)
    content          = Column(Text, nullable=False)
    category         = Column(String(100), nullable=True)
    effective_date   = Column(String(20), nullable=True)
    created_at       = Column(String(30), nullable=False)

    paragraph = relationship("Paragraph", back_populates="subparagraphs")
    items     = relationship("Item", back_populates="subparagraph",
                             cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    subparagraph_id  = Column(Integer, ForeignKey("subparagraphs.id"), nullable=False, index=True)
    item_no          = Column(String(10), nullable=False)
    content          = Column(Text, nullable=False)
    category         = Column(String(100), nullable=True)
    effective_date   = Column(String(20), nullable=True)
    created_at       = Column(String(30), nullable=False)

    subparagraph = relationship("Subparagraph", back_populates="items")
```

#### 6.1.2 Pydantic 스키마 (`app/schemas/chat.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None
    compliance_data: Optional["ComplianceData"] = None

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)
    session_id: str = Field(..., min_length=1, max_length=100)
    history: List[ChatMessage] = Field(default_factory=list, max_length=40)

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
    disclaimer: str = "본 결과는 참고용이며, 법적 효력이 없습니다. 정확한 법률 해석은 전문가에게 문의하세요."

class ExportRequest(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    project_summary: str = Field(..., max_length=500)
```

#### 6.1.3 RAG 서비스 (`app/services/rag_service.py`)

```python
from sqlalchemy.orm import Session
from app.models.law import Article, Paragraph
from typing import List

class RAGService:
    def __init__(self, db: Session):
        self.db = db

    def search_relevant_articles(self, query: str, top_k: int = 5) -> List[dict]:
        """
        사용자 쿼리와 관련된 조항을 키워드 기반으로 검색.
        현재 구현: SQLite FTS 또는 LIKE 검색.
        향후 개선: 임베딩 기반 벡터 검색으로 교체 가능.
        """
        ...

    def build_context(self, articles: List[dict]) -> str:
        """검색된 조항들을 GPT 프롬프트용 컨텍스트 문자열로 변환."""
        ...

    def build_system_prompt(self, context: str) -> str:
        """시스템 프롬프트 구성 (법령 컨텍스트 + 분석 지시)."""
        ...
```

#### 6.1.4 OpenAI 서비스 (`app/services/openai_service.py`)

```python
import asyncio
from openai import AsyncOpenAI
from typing import AsyncGenerator

class OpenAIService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
        self.timeout = 60.0
        self.max_retries = 3

    async def stream_chat(
        self,
        system_prompt: str,
        messages: list,
        user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        GPT-4o mini 스트리밍 응답 생성.
        실패 시 exponential backoff로 최대 3회 재시도.
        """
        ...

    async def parse_law_structure(self, text_chunk: str) -> dict:
        """
        법령 텍스트 청크를 구조화된 JSON으로 파싱.
        비스트리밍 호출.
        """
        ...
```

#### 6.1.5 Rate Limiter 미들웨어 (`app/middleware/rate_limiter.py`)

```python
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException

class SlidingWindowRateLimiter:
    """
    슬라이딩 윈도우 알고리즘 기반 IP Rate Limiter.
    인메모리 딕셔너리로 관리 (서버 재시작 시 초기화 허용).
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # { ip_address: [timestamp1, timestamp2, ...] }
        self._request_log: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        """현재 요청이 허용되는지 확인하고, 허용 시 타임스탬프 기록."""
        now = time.time()
        window_start = now - self.window_seconds

        # 윈도우 밖의 오래된 타임스탬프 제거
        self._request_log[ip] = [
            ts for ts in self._request_log[ip] if ts > window_start
        ]

        if len(self._request_log[ip]) >= self.max_requests:
            return False

        self._request_log[ip].append(now)
        return True

    def get_retry_after(self, ip: str) -> int:
        """해당 IP의 가장 오래된 요청이 만료되기까지 남은 초."""
        if not self._request_log[ip]:
            return 0
        oldest = min(self._request_log[ip])
        return max(0, int(self.window_seconds - (time.time() - oldest)))
```

---

### 6.2 프론트엔드 컴포넌트

#### 6.2.1 컴포넌트 트리

```
App
└── ChatWindow
    ├── DisclaimerBanner          # 면책 조항 상단 고정 배너
    ├── MessageList
    │   └── MessageBubble[]       # role에 따라 좌/우 정렬
    │       └── ComplianceCard    # compliance_data 있을 때 렌더링
    ├── LoadingIndicator          # isStreaming 상태일 때 표시
    ├── InputBar                  # 텍스트 입력 + 전송 버튼
    └── ExportButton              # PDF 내보내기 버튼
```

#### 6.2.2 TypeScript 타입 정의 (`src/types/index.ts`)

```typescript
export type MessageRole = 'user' | 'assistant';

export type ComplianceStatus = 'Compliant' | 'Partially Compliant' | 'Non-Compliant';
export type Priority = '높음' | '중간' | '낮음';

export interface ComplianceItem {
  article_no: string;
  title: string;
  status: ComplianceStatus;
  priority: Priority;
  recommendation?: string;
  article_summary?: string;
}

export interface ComplianceData {
  overall: ComplianceStatus;
  items: ComplianceItem[];
  disclaimer: string;
}

export interface ChatMessage {
  id: string;                    // 클라이언트 생성 UUID
  role: MessageRole;
  content: string;
  timestamp: Date;
  compliance_data?: ComplianceData;
}

export interface ChatSession {
  sessionId: string;             // UUID v4
  messages: ChatMessage[];
  createdAt: Date;
  lastActiveAt: Date;
}
```

#### 6.2.3 useChatSession 훅 (`src/hooks/useChatSession.ts`)

```typescript
interface UseChatSessionReturn {
  session: ChatSession;
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  exportPDF: () => Promise<void>;
  clearSession: () => void;
}

// sessionStorage 키: "chat_session"
// 세션 만료: lastActiveAt 기준 30분 초과 시 자동 초기화
export function useChatSession(): UseChatSessionReturn { ... }
```

#### 6.2.4 useSSE 훅 (`src/hooks/useSSE.ts`)

```typescript
interface SSEOptions {
  onChunk: (chunk: string) => void;
  onDone: (complianceData: ComplianceData) => void;
  onError: (error: string) => void;
}

// fetch API + ReadableStream으로 SSE 처리
// EventSource 대신 fetch 사용 (POST body 전송 필요)
export function useSSE(options: SSEOptions) {
  const sendRequest: (url: string, body: object) => Promise<void>;
  return { sendRequest };
}
```

---

## 7. 데이터 모델 (Data Models)

### 7.1 법령 파싱 스키마 (`app/schemas/law.py`)

```python
from pydantic import BaseModel
from typing import List, Optional

class ItemSchema(BaseModel):
    item_no: str           # "가.", "나."
    content: str

class SubparagraphSchema(BaseModel):
    subparagraph_no: str   # "1.", "2."
    content: str
    items: List[ItemSchema] = []

class ParagraphSchema(BaseModel):
    paragraph_no: str      # "①", "②"
    content: str
    subparagraphs: List[SubparagraphSchema] = []

class ArticleSchema(BaseModel):
    article_no: str        # "제1조"
    title: str             # "목적"
    content: Optional[str] = None
    category: Optional[str] = None
    effective_date: Optional[str] = None
    paragraphs: List[ParagraphSchema] = []

class ParsedLawSchema(BaseModel):
    articles: List[ArticleSchema]
    total_articles: int
    parsed_at: str

class ParseLawResponse(BaseModel):
    status: str
    message: str
    stats: dict
    processed_at: str
```

### 7.2 세션 데이터 (프론트엔드 sessionStorage)

```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "얼굴 인식 기반 출입 통제 시스템을 개발하려고 합니다.",
      "timestamp": "2025-01-15T10:30:00.000Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "분석 결과입니다...",
      "timestamp": "2025-01-15T10:30:15.000Z",
      "compliance_data": {
        "overall": "Partially Compliant",
        "items": [...],
        "disclaimer": "본 결과는 참고용이며..."
      }
    }
  ],
  "createdAt": "2025-01-15T10:29:00.000Z",
  "lastActiveAt": "2025-01-15T10:30:15.000Z"
}
```

---

## 8. 핵심 비즈니스 로직

### 8.1 RAG 파이프라인 (Query Expansion + 임베딩 벡터 검색)

```
사용자 질문
    │
    ▼
[1] Query Expansion (GPT-4o mini)
    - 사용자 입력을 GPT에 전달하여 법적 쟁점 키워드 추출
    - 프롬프트 예시:
      "다음 AI 프로젝트 설명에서 한국 AI 기본법과 관련된
       핵심 법적 쟁점 키워드를 5개 이내로 추출하세요.
       예: 고위험AI, 생체정보, 투명성, 설명가능성, 개인정보
       설명: {user_input}"
    - 결과: ["고위험AI", "생체정보처리", "출입통제", ...]
    │
    ▼
[2] 검색 쿼리 구성
    - 원본 질문 + 추출된 키워드를 결합한 검색 텍스트 생성
    - 예: "얼굴 인식 출입 통제 시스템 고위험AI 생체정보처리"
    │
    ▼
[3] 임베딩 기반 벡터 검색
    - 검색 텍스트를 text-embedding-3-small로 임베딩
    - SQLite embeddings 테이블에서 모든 조항 벡터 로드
    - numpy 코사인 유사도 계산: similarity = dot(q, d) / (|q| * |d|)
    - 상위 5개 조항 반환
    - (임베딩 없으면 LIKE 기반 키워드 검색으로 폴백)
    │
    ▼
[4] 컨텍스트 구성
    - 검색된 조항들을 구조화된 텍스트로 변환
    - 형식: "제N조(제목): 내용\n  ① 항 내용\n    1. 호 내용"
    │
    ▼
[5] 시스템 프롬프트 구성
    ┌─────────────────────────────────────────────────────┐
    │ 당신은 한국 AI 기본법 전문 분석 어시스턴트입니다.   │
    │                                                     │
    │ [관련 법령 조항]                                    │
    │ {context}                                           │
    │                                                     │
    │ 분석 지침:                                          │
    │ 1. 각 항목을 Compliant/Partially Compliant/         │
    │    Non-Compliant로 분류하세요.                      │
    │ 2. 관련 조항 번호를 반드시 명시하세요.              │
    │ 3. 미준수/부분준수 항목에 개선 권고사항을 제시하세요│
    │ 4. 우선순위(높음/중간/낮음)를 함께 제시하세요.     │
    │ 5. 면책 조항을 응답 마지막에 포함하세요.            │
    └─────────────────────────────────────────────────────┘
    │
    ▼
[6] GPT-4o mini 스트리밍 호출
    - messages: [system, ...history, user]
    - stream=True
    │
    ▼
[7] SSE 청크 전송
    - 각 delta.content를 즉시 클라이언트로 전송
    - 스트림 완료 시 done 이벤트 전송
```

### 8.2 AI 기본법 파싱 파이프라인

```
backend/data/ai_basic_law.pdf
    │
    ▼
[1] pdfplumber 텍스트 추출
    - 전체 페이지 텍스트 추출
    - 페이지 번호, 헤더/푸터 제거
    │
    ▼
[2] 청크 분할
    - 조(Article) 단위로 분할
    - 정규식: r'제\d+조\s*\([^)]+\)'
    - 각 청크: 약 500~1000자
    │
    ▼
[3] GPT-4o mini 구조화 파싱 (청크별)
    프롬프트:
    ┌─────────────────────────────────────────────────────┐
    │ 다음 법령 텍스트를 JSON 구조로 파싱하세요.          │
    │ 형식: {"article_no": "제N조", "title": "...",       │
    │        "paragraphs": [{"paragraph_no": "①",        │
    │        "content": "...", "subparagraphs": [...]}]}  │
    │                                                     │
    │ 텍스트: {chunk}                                     │
    └─────────────────────────────────────────────────────┘
    │
    ▼
[4] JSON 검증 (Pydantic ArticleSchema)
    │
    ▼
[5] SQLite 트랜잭션 저장
    - BEGIN TRANSACTION
    - 기존 데이터 전체 삭제 (DELETE FROM items, subparagraphs, paragraphs, articles)
    - 새 데이터 INSERT
    - COMMIT (실패 시 ROLLBACK)
```

### 8.3 IP Rate Limiting (슬라이딩 윈도우)

```
요청 수신 (IP: x.x.x.x)
    │
    ▼
[1] 현재 시각 = now
    윈도우 시작 = now - 600초
    │
    ▼
[2] request_log[ip]에서 window_start 이전 타임스탬프 제거
    │
    ▼
[3] len(request_log[ip]) >= 5?
    │
    ├── YES ──► HTTP 429 반환
    │           Retry-After: {남은 초}
    │           {"detail": "요청 한도를 초과했습니다. 10분 후에 다시 시도해주세요."}
    │
    └── NO ───► request_log[ip].append(now)
                요청 처리 계속
```

### 8.4 세션 관리 (프론트엔드)

```
앱 초기화
    │
    ▼
sessionStorage에서 "chat_session" 로드
    │
    ├── 없음 ──► 새 세션 생성 (UUID v4 sessionId)
    │
    └── 있음 ──► lastActiveAt 확인
                    │
                    ├── 30분 초과 ──► 세션 만료 안내 + 새 세션 생성
                    │
                    └── 30분 이내 ──► 기존 세션 복원
```

### 8.5 PDF 내보내기 파이프라인

```
ExportRequest (messages, project_summary)
    │
    ▼
[1] Jinja2 템플릿 렌더링 (export_report.html)
    - 분석 일시
    - 프로젝트 요약
    - 전체 준수 등급
    - 주요 개선 권고사항 (우선순위 순)
    - 면책 조항
    │
    ▼
[2] WeasyPrint HTML → PDF 변환
    │
    ▼
[3] PDF 바이너리 반환 (StreamingResponse)
    Content-Type: application/pdf
    Content-Disposition: attachment; filename="..."
```

---

## 9. 환경변수 목록

### 9.1 백엔드 (`backend/.env.example`)

```dotenv
# OpenAI
OPENAI_API_KEY=sk-...

# 관리자 인증
ADMIN_SECRET_KEY=your-strong-secret-key-here

# 데이터베이스
DATABASE_URL=sqlite:///./data/ai_basic_law.db

# 법령 파일 경로
LAW_PDF_PATH=./data/ai_basic_law.pdf

# 폰트 디렉토리 경로 (WeasyPrint PDF 생성용)
FONT_DIR=./data/fonts

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=5
RATE_LIMIT_WINDOW_SECONDS=600

# CORS (프론트엔드 URL)
ALLOWED_ORIGINS=http://localhost:5173

# 로깅
LOG_LEVEL=INFO
```

### 9.2 프론트엔드 (`frontend/.env.example`)

```dotenv
# 백엔드 API URL
VITE_API_BASE_URL=http://localhost:8000

# 세션 만료 시간 (밀리초, 기본 30분)
VITE_SESSION_TIMEOUT_MS=1800000
```

---

## 10. 폰트 설정 (Font Configuration)

### 10.1 프론트엔드 (Tailwind CSS + @font-face)

커스텀 폰트 파일 5개는 `frontend/public/fonts/`에 위치하며, `index.css`에서 `@font-face`로 선언한다.

```css
/* frontend/src/styles/index.css */
@font-face {
  font-family: 'KBFGDisplay';
  src: url('/fonts/KBFGDisplay-Light.ttf') format('truetype');
  font-weight: 300;
  font-style: normal;
}
@font-face {
  font-family: 'KBFGDisplay';
  src: url('/fonts/KBFGDisplay-Medium.ttf') format('truetype');
  font-weight: 500;
  font-style: normal;
}
@font-face {
  font-family: 'KBFGText';
  src: url('/fonts/KBFGText-Light.ttf') format('truetype');
  font-weight: 300;
  font-style: normal;
}
@font-face {
  font-family: 'KBFGText';
  src: url('/fonts/KBFGText-Medium.ttf') format('truetype');
  font-weight: 500;
  font-style: normal;
}
@font-face {
  font-family: 'KBFGText';
  src: url('/fonts/KBFGText-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}

@tailwind base;
@tailwind components;
@tailwind utilities;
```

`tailwind.config.ts`에서 두 폰트 패밀리를 등록한다. Display는 제목/헤더, Text는 본문/UI 요소에 사용한다:

```typescript
// frontend/tailwind.config.ts
export default {
  theme: {
    extend: {
      fontFamily: {
        display: ['KBFGDisplay', 'sans-serif'],  // 제목, 헤더
        sans: ['KBFGText', 'sans-serif'],         // 본문, UI 기본값
      },
    },
  },
}
```

**폰트 사용 가이드**

| 용도 | 폰트 | weight |
|------|------|--------|
| 페이지 제목 | KBFGDisplay | Medium (500) |
| 섹션 제목 | KBFGDisplay | Light (300) |
| 본문 텍스트 | KBFGText | Medium (500) |
| 보조 텍스트 | KBFGText | Light (300) |
| 강조 텍스트 | KBFGText | Bold (700) |

### 10.2 백엔드 PDF (WeasyPrint)

폰트 파일 5개는 `backend/data/fonts/`에 위치하며, Jinja2 HTML 템플릿에서 절대 경로로 참조한다.

```html
<!-- backend/app/templates/export_report.html -->
<style>
  @font-face {
    font-family: 'KBFGDisplay';
    src: url('file:///{{ font_dir }}/KBFGDisplay-Light.ttf') format('truetype');
    font-weight: 300;
  }
  @font-face {
    font-family: 'KBFGDisplay';
    src: url('file:///{{ font_dir }}/KBFGDisplay-Medium.ttf') format('truetype');
    font-weight: 500;
  }
  @font-face {
    font-family: 'KBFGText';
    src: url('file:///{{ font_dir }}/KBFGText-Light.ttf') format('truetype');
    font-weight: 300;
  }
  @font-face {
    font-family: 'KBFGText';
    src: url('file:///{{ font_dir }}/KBFGText-Medium.ttf') format('truetype');
    font-weight: 500;
  }
  @font-face {
    font-family: 'KBFGText';
    src: url('file:///{{ font_dir }}/KBFGText-Bold.ttf') format('truetype');
    font-weight: 700;
  }

  body { font-family: 'KBFGText', sans-serif; font-weight: 500; }
  h1, h2 { font-family: 'KBFGDisplay', sans-serif; font-weight: 500; }
  h3 { font-family: 'KBFGDisplay', sans-serif; font-weight: 300; }
</style>
```

`font_dir`는 `pdf_export_service.py`에서 환경변수 `FONT_DIR`의 절대 경로를 템플릿에 주입한다.

> **주의**: WeasyPrint에서 로컬 파일을 참조할 때는 반드시 `file:///` 프로토콜과 절대 경로를 사용해야 한다. 상대 경로는 동작하지 않는다.

---

## 11. 정확성 속성 (Correctness Properties)

*속성(Property)이란 시스템의 모든 유효한 실행에서 참이어야 하는 특성 또는 동작이다. 즉, 시스템이 무엇을 해야 하는지에 대한 형식적 명세다. 속성은 사람이 읽을 수 있는 명세와 기계가 검증할 수 있는 정확성 보장 사이의 다리 역할을 한다.*

### Property 1: 입력 길이 경계 검증

*임의의* 5,000자를 초과하는 문자열 입력에 대해, 시스템은 항상 HTTP 400 응답을 반환해야 하며 OpenAI API를 호출해서는 안 된다. 반대로 5,000자 이하의 유효한 입력은 항상 처리되어야 한다.

**Validates: Requirements 1.3, 1.4**

---

### Property 2: 응답 구조 완전성

*임의의* 유효한 AI 프로젝트 설명에 대해, 챗봇 응답은 항상 (1) 전체 준수 등급(Compliant/Partially Compliant/Non-Compliant 중 하나), (2) 관련 AI 기본법 조항 번호, (3) 면책 조항 문구를 포함해야 한다.

**Validates: Requirements 2.2, 2.3**

---

### Property 3: 개선 권고사항 구조 완전성

*임의의* 미준수 또는 부분 준수 항목을 포함하는 분석 결과에 대해, 각 해당 항목은 항상 (1) 우선순위(높음/중간/낮음 중 하나), (2) 구체적인 개선 권고사항, (3) 관련 조항 요약을 포함해야 한다.

**Validates: Requirements 3.1, 3.2, 3.3**

---

### Property 4: 세션 만료 감지

*임의의* 세션에 대해, lastActiveAt으로부터 30분이 경과한 경우 시스템은 항상 해당 세션을 만료 상태로 판단해야 한다. 30분 미만인 경우는 항상 활성 상태로 판단해야 한다.

**Validates: Requirements 4.3**

---

### Property 5: PDF 내용 완전성

*임의의* 대화 내역과 프로젝트 요약으로 생성된 PDF는 항상 (1) 분석 일시, (2) 프로젝트 요약, (3) 준수 등급 요약, (4) 주요 개선 권고사항을 포함해야 한다.

**Validates: Requirements 5.2, 5.3**

---

### Property 6: 법령 파싱 라운드트립

*임의의* 유효한 법령 텍스트 청크에 대해, GPT 파싱 후 DB에 저장하고 다시 조회했을 때 원본 조항 번호와 내용이 보존되어야 한다.

**Validates: Requirements 6.2, 6.3**

---

### Property 7: 관리자 인증 키 검증

*임의의* 요청에 대해, X-Admin-Key 헤더가 없거나 ADMIN_SECRET_KEY와 일치하지 않으면 항상 HTTP 401을 반환해야 한다. 올바른 키가 제공된 경우에만 파싱 로직이 실행되어야 한다.

**Validates: Requirements 6.4, 6.5**

---

### Property 8: Rate Limiting 슬라이딩 윈도우

*임의의* IP 주소에 대해, 10분 슬라이딩 윈도우 내에서 5회 이하의 요청은 항상 허용되어야 하고, 6번째 이상의 요청은 항상 HTTP 429로 차단되어야 한다. 가장 오래된 요청이 윈도우 밖으로 나가면 새 요청이 허용되어야 한다.

**Validates: Requirements 7.1, 7.2, 7.4**

---

### Property 9: 메시지 순서 보존

*임의의* 대화 내역에 대해, MessageList 컴포넌트는 항상 메시지를 timestamp 오름차순으로 렌더링해야 하며, 사용자 메시지와 어시스턴트 메시지는 시각적으로 구분되어야 한다.

**Validates: Requirements 8.3**

---

## 12. 오류 처리 전략 (Error Handling)

### 11.1 OpenAI API 실패 재시도 로직

```python
import asyncio
from openai import APIError, APITimeoutError, RateLimitError

async def call_with_retry(func, *args, max_retries=3, **kwargs):
    """
    Exponential backoff 재시도 로직.
    대기 시간: 1초, 2초, 4초
    """
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except RateLimitError:
            # OpenAI Rate Limit: 재시도 의미 없음, 즉시 실패
            raise
        except (APITimeoutError, APIError) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # attempt=0: 1초, attempt=1: 2초
            await asyncio.sleep(wait_time)
```

### 11.2 오류 응답 표준화

모든 오류 응답은 다음 형식을 따른다:

```json
{
  "detail": "오류 메시지 (한국어)",
  "error_code": "OPENAI_TIMEOUT",
  "retry_after": 60
}
```

| error_code | HTTP 코드 | 설명 |
|------------|-----------|------|
| INPUT_TOO_LONG | 400 | 5000자 초과 입력 |
| RATE_LIMIT_EXCEEDED | 429 | IP Rate Limit 초과 |
| OPENAI_TIMEOUT | 503 | OpenAI 60초 타임아웃 |
| OPENAI_ERROR | 503 | OpenAI API 오류 (3회 재시도 후) |
| PARSE_ERROR | 500 | 법령 파싱 실패 |
| PDF_GENERATION_ERROR | 500 | PDF 생성 실패 |
| UNAUTHORIZED | 401 | 관리자 키 인증 실패 |

### 11.3 파싱 실패 시 트랜잭션 롤백

```python
async def parse_and_save(db: Session, pdf_path: str):
    try:
        # 1. PDF 텍스트 추출
        text = extract_text(pdf_path)
        # 2. 청크 분할 및 GPT 파싱
        articles = await parse_chunks(text)
        # 3. 트랜잭션 시작
        db.begin()
        # 4. 기존 데이터 삭제
        db.execute("DELETE FROM items")
        db.execute("DELETE FROM subparagraphs")
        db.execute("DELETE FROM paragraphs")
        db.execute("DELETE FROM articles")
        # 5. 새 데이터 삽입
        for article in articles:
            save_article(db, article)
        # 6. 커밋
        db.commit()
    except Exception as e:
        db.rollback()
        raise ParseError(f"파싱 실패: {str(e)}")
```

### 11.4 SSE 스트리밍 오류 처리

스트리밍 중 오류 발생 시 error 이벤트를 전송하고 스트림을 종료한다:

```
data: {"type": "error", "message": "OpenAI API 연결에 실패했습니다. 잠시 후 다시 시도해주세요."}

data: [DONE]
```

---

## 13. 테스트 전략 (Testing Strategy)

### 12.1 이중 테스트 접근법

단위 테스트와 속성 기반 테스트를 병행한다. 단위 테스트는 구체적인 예시와 엣지 케이스를 검증하고, 속성 기반 테스트는 임의의 입력에 대한 보편적 속성을 검증한다.

### 12.2 속성 기반 테스트 (Property-Based Testing)

**라이브러리**: `hypothesis` (Python)

각 속성 테스트는 최소 100회 이상 실행되며, 다음 태그 형식으로 주석을 달아 설계 문서와 연결한다:

```
# Feature: ai-basic-law-chatbot, Property {번호}: {속성 설명}
```

**속성 테스트 예시**:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

# Feature: ai-basic-law-chatbot, Property 1: 입력 길이 경계 검증
@given(st.text(min_size=5001, max_size=10000))
@settings(max_examples=100)
def test_input_too_long_returns_400(text):
    response = client.post("/api/chat", json={"message": text, ...})
    assert response.status_code == 400

# Feature: ai-basic-law-chatbot, Property 8: Rate Limiting 슬라이딩 윈도우
@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_rate_limit_allows_up_to_5_requests(n):
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=600)
    for _ in range(n):
        assert limiter.is_allowed("192.168.1.1") is True

# Feature: ai-basic-law-chatbot, Property 4: 세션 만료 감지
@given(st.integers(min_value=1801, max_value=7200))
@settings(max_examples=100)
def test_session_expired_after_30_minutes(elapsed_seconds):
    session = create_session_with_age(elapsed_seconds)
    assert is_session_expired(session) is True
```

### 12.3 단위 테스트

**라이브러리**: `pytest` + `pytest-asyncio`

| 테스트 파일 | 대상 | 테스트 유형 |
|-------------|------|-------------|
| test_rate_limiter.py | SlidingWindowRateLimiter | 단위, 속성 |
| test_law_parser.py | LawParserService | 단위, 속성 |
| test_chat.py | /api/chat 엔드포인트 | 통합 |
| test_pdf_export.py | PDFExportService | 단위, 속성 |
| test_admin.py | /admin/parse-law | 통합 |

**주요 단위 테스트 케이스**:

- OpenAI API 모킹 후 재시도 로직 3회 동작 확인
- X-Admin-Key 없음 → 401 반환 확인
- X-Admin-Key 불일치 → 401 반환 확인
- 파싱 실패 시 DB 롤백 확인 (트랜잭션 무결성)
- PDF 생성 결과에 필수 항목 포함 여부 확인
- SSE 스트림 정상 종료 확인

### 12.4 프론트엔드 테스트

**라이브러리**: `vitest` + `@testing-library/react`

```bash
# 단일 실행 (watch 모드 아님)
npx vitest --run
```

| 테스트 | 대상 |
|--------|------|
| useChatSession 세션 만료 로직 | Property 4 |
| MessageList 메시지 순서 렌더링 | Property 9 |
| InputBar 5000자 초과 입력 차단 | Property 1 |

---

---

## 14. 가이드라인 임베딩 및 법령 연관 태깅

### 14.1 guideline_chunks 테이블

```sql
CREATE TABLE guideline_chunks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT    NOT NULL,   -- 파일명
    page_no          INTEGER,            -- 페이지 번호
    content          TEXT    NOT NULL,   -- 청크 텍스트
    vector           BLOB    NOT NULL,   -- 임베딩 벡터 (numpy float32)
    model            TEXT    NOT NULL DEFAULT 'text-embedding-3-small',
    related_articles TEXT,               -- JSON 배열: ["제3조", "제22조"]
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### 14.2 가이드라인 처리 파이프라인

```
data/guidelines/*.pdf
    │
    ├── 텍스트 추출 가능 → pdfplumber → 페이지 단위 청크
    └── 스캔본(이미지) → GPT-4o Vision OCR → 페이지 단위 청크
    │
    ▼
text-embedding-3-small 임베딩 → guideline_chunks 저장
    │
    ▼
POST /admin/tag-guidelines
    │
    ▼
각 청크 → GPT-4o mini → 관련 조항 번호 추출 → related_articles 저장
```

### 14.3 태깅 프롬프트

```
다음 AI 가이드라인 텍스트가 한국 AI 기본법의 어떤 조항과 관련되는지
조항 번호만 JSON 배열로 반환하세요. 관련 없으면 빈 배열 []을 반환하세요.
예: ["제3조", "제22조"]

텍스트: {chunk.content}
```

### 14.4 태그 기반 RAG 검색 흐름

```
사용자 질문
    │
    ▼
Query Expansion → 키워드 추출
    │
    ▼
임베딩 유사도 → 법령 조항 3개 검색
    │
    ▼
검색된 조항 번호(예: 제22조)로 related_articles 필터링
→ 태그된 가이드라인 청크 우선 반환 (최대 2개)
→ 태그 없으면 임베딩 유사도로 가이드라인 청크 2개 검색
    │
    ▼
GPT 컨텍스트: [관련 법령 조항] + [관련 가이드라인]
```

### 14.5 새 관리자 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /admin/embed-guideline` | 텍스트 추출 가능 PDF 임베딩 |
| `POST /admin/embed-guideline-ocr` | 스캔본 PDF OCR + 임베딩 |
| `POST /admin/tag-guidelines` | 가이드라인 청크 법령 조항 자동 태깅 |
