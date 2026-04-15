# 구현 계획: AI 기본법 준수 확인 챗봇

## 개요

FastAPI 백엔드 + React 프론트엔드 모노레포 구조로 AI 기본법 준수 여부를 분석하는 챗봇 서비스를 구현한다.
RAG 파이프라인(SQLite + GPT-4o mini), SSE 스트리밍, IP Rate Limiting, PDF 내보내기를 단계적으로 구현한다.

---

## 태스크 목록

- [ ] 1. 프로젝트 기반 구조 설정
  - [ ] 1.1 백엔드 디렉토리 구조 및 의존성 파일 생성
    - `backend/` 하위 디렉토리 구조 생성 (`app/models`, `app/schemas`, `app/routers`, `app/services`, `app/middleware`, `app/templates`)
    - `backend/requirements.txt` 작성 (fastapi, uvicorn, sqlalchemy, alembic, openai, pdfplumber, weasyprint, jinja2, python-dotenv, pytest, pytest-asyncio, hypothesis)
    - `backend/.env.example` 작성 (OPENAI_API_KEY, ADMIN_SECRET_KEY, DATABASE_URL, LAW_PDF_PATH, FONT_DIR, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, ALLOWED_ORIGINS, LOG_LEVEL)
    - _요구사항: 1.1 (기술 스택), 1.3 (LLM 연동), 1.4 (데이터베이스)_

  - [ ] 1.2 프론트엔드 디렉토리 구조 및 의존성 파일 생성
    - `frontend/` 하위 디렉토리 구조 생성 (`src/components`, `src/hooks`, `src/api`, `src/types`, `src/styles`)
    - `frontend/package.json` 작성 (react, react-dom, typescript, vite, tailwindcss, @testing-library/react, vitest)
    - `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts` 작성
    - `frontend/.env.example` 작성 (VITE_API_BASE_URL, VITE_SESSION_TIMEOUT_MS)
    - _요구사항: 8.1 (React 기반 웹 인터페이스)_

- [ ] 2. 백엔드 핵심 설정 및 DB 모델 구현
  - [ ] 2.1 환경변수 설정 및 FastAPI 앱 진입점 구현
    - `backend/app/config.py`: pydantic BaseSettings로 환경변수 로드 (OPENAI_API_KEY, ADMIN_SECRET_KEY, DATABASE_URL, LAW_PDF_PATH, FONT_DIR, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, ALLOWED_ORIGINS, LOG_LEVEL)
    - `backend/app/database.py`: SQLAlchemy 엔진, 세션 팩토리, Base 클래스 정의
    - `backend/app/main.py`: FastAPI 앱 생성, CORS 미들웨어 등록, 라우터 포함, 로깅 설정
    - _요구사항: 1.3 (API 키 환경변수 관리), 3.2 (보안)_

  - [ ] 2.2 SQLAlchemy ORM 모델 구현
    - `backend/app/models/law.py`: Article, Paragraph, Subparagraph, Item 클래스 구현
    - 각 모델에 id, 상위 FK, 번호, content, category, effective_date, created_at 필드 정의
    - relationship 및 cascade="all, delete-orphan" 설정
    - _요구사항: 1.4 (DB 스키마 4단계 계층 구조)_

  - [ ] 2.3 Alembic 마이그레이션 초기 설정
    - `backend/alembic.ini`, `backend/migrations/env.py` 작성
    - 초기 마이그레이션 파일 생성 (articles, paragraphs, subparagraphs, items 테이블 + 인덱스)
    - _요구사항: 1.4 (마이그레이션 구조)_

- [ ] 3. Pydantic 스키마 구현
  - [ ] 3.1 채팅 요청/응답 스키마 구현
    - `backend/app/schemas/chat.py`: ChatMessage, ChatRequest, ComplianceItem, ComplianceData, ExportRequest 클래스 구현
    - ChatRequest: message(max_length=5000), session_id, history(max_length=40) 필드
    - ComplianceItem: article_no, title, status(Literal), priority(Literal), recommendation, article_summary 필드
    - _요구사항: 1.3, 2.2, 3.1, 3.2_

  - [ ] 3.2 법령 파싱 스키마 구현
    - `backend/app/schemas/law.py`: ItemSchema, SubparagraphSchema, ParagraphSchema, ArticleSchema, ParsedLawSchema, ParseLawResponse 클래스 구현
    - 계층 구조 중첩 관계 반영 (ArticleSchema → ParagraphSchema → SubparagraphSchema → ItemSchema)
    - _요구사항: 6.2 (조→항→호→목 계층 구조 파싱)_

- [ ] 4. IP Rate Limiter 미들웨어 구현
  - [ ] 4.1 슬라이딩 윈도우 Rate Limiter 구현
    - `backend/app/middleware/rate_limiter.py`: SlidingWindowRateLimiter 클래스 구현
    - `is_allowed(ip)`: 윈도우 밖 타임스탬프 제거 후 요청 수 확인 및 기록
    - `get_retry_after(ip)`: 가장 오래된 요청 만료까지 남은 초 반환
    - FastAPI 의존성 주입용 `check_rate_limit` 함수 구현 (HTTP 429 + Retry-After 헤더 반환)
    - _요구사항: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 4.2 Rate Limiter 속성 기반 테스트 작성
    - **Property 8: Rate Limiting 슬라이딩 윈도우**
    - **Validates: Requirements 7.1, 7.2, 7.4**
    - `backend/tests/test_rate_limiter.py`: hypothesis로 1~5회 요청은 항상 허용, 6번째 이상은 항상 차단 검증
    - 윈도우 만료 후 새 요청 허용 검증

- [ ] 5. OpenAI 서비스 구현
  - [ ] 5.1 OpenAI 스트리밍 및 재시도 로직 구현
    - `backend/app/services/openai_service.py`: OpenAIService 클래스 구현
    - `stream_chat()`: GPT-4o mini 스트리밍 응답 생성 (AsyncGenerator)
    - `parse_law_structure()`: 법령 텍스트 청크 구조화 파싱 (비스트리밍)
    - `call_with_retry()`: exponential backoff 재시도 로직 (최대 3회, 대기 1초/2초/4초)
    - RateLimitError는 즉시 실패, APITimeoutError/APIError는 재시도
    - 타임아웃 60초 설정
    - _요구사항: 1.3 (재시도 로직, 타임아웃), 2.5 (오류 시 재시도 안내)_

- [ ] 6. RAG 서비스 구현
  - [ ] 6.1 임베딩 서비스 구현
    - `backend/app/services/embedding_service.py`: EmbeddingService 클래스 구현
    - `create_embedding(text)`: OpenAI text-embedding-3-small로 텍스트 임베딩 생성
    - `embed_all_articles(db)`: DB의 모든 조항을 임베딩하여 embeddings 테이블에 저장
    - `cosine_similarity(v1, v2)`: numpy 코사인 유사도 계산
    - `search_by_vector(db, query_vector, top_k=5)`: 벡터 유사도 기반 상위 조항 검색
    - _요구사항: 2.2, 제약사항 1.8_

  - [ ] 6.2 Query Expansion 및 RAG 서비스 구현
    - `backend/app/services/rag_service.py`: RAGService 클래스 구현
    - `expand_query(query)`: GPT-4o mini로 법적 쟁점 키워드 추출 (Query Expansion)
    - `search_relevant_articles(query, top_k=5)`: Query Expansion → 임베딩 검색 → 상위 5개 반환 (임베딩 없으면 LIKE 폴백)
    - `build_context(articles)`: 검색된 조항을 "제N조(제목): 내용\n  ① 항 내용" 형식 문자열로 변환
    - `build_system_prompt(context)`: 법령 컨텍스트 + 분석 지침 포함 시스템 프롬프트 구성
    - _요구사항: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

  - [ ] 6.3 POST /admin/embed-law 엔드포인트 구현
    - `backend/app/routers/admin.py`에 POST /admin/embed-law 추가
    - X-Admin-Key 헤더 검증
    - EmbeddingService.embed_all_articles() 호출
    - 성공 시 임베딩된 조항 수 반환
    - _요구사항: 6.4, 6.5, 제약사항 1.8_

  - [ ] 6.4 ORM 모델에 Embedding 추가
    - `backend/app/models/law.py`에 Embedding 클래스 추가
    - article_id (FK, UNIQUE), vector (LargeBinary), model, created_at 필드
    - _요구사항: 제약사항 1.4_

- [ ] 7. 채팅 라우터 구현 (SSE 스트리밍)
  - [ ] 7.1 POST /api/chat 엔드포인트 구현
    - `backend/app/routers/chat.py`: POST /api/chat 엔드포인트 구현
    - Rate Limiter 의존성 주입 적용
    - 입력 검증: message 5,000자 초과 시 HTTP 400 + INPUT_TOO_LONG 반환
    - RAGService로 관련 조항 검색 → 시스템 프롬프트 구성
    - OpenAIService.stream_chat()으로 SSE 스트리밍 응답 생성
    - SSE 이벤트 타입: chunk(텍스트 청크), done(ComplianceData 포함), error(오류 메시지)
    - StreamingResponse(media_type="text/event-stream") 반환
    - OpenAI 오류 시 SSE error 이벤트 전송 후 스트림 종료
    - _요구사항: 1.1, 1.2, 1.3, 1.4, 2.1~2.5, 7.1~7.4_

  - [ ]* 7.2 입력 길이 경계 속성 기반 테스트 작성
    - **Property 1: 입력 길이 경계 검증**
    - **Validates: Requirements 1.3, 1.4**
    - `backend/tests/test_chat.py`: hypothesis로 5001~10000자 임의 문자열 입력 시 항상 HTTP 400 반환 검증
    - 5000자 이하 유효 입력은 항상 처리됨 검증 (OpenAI 모킹)

- [ ] 8. 대화 내용 복사 기능 구현
  - [ ] 8.1 CopyButton 컴포넌트 구현
    - `frontend/src/components/CopyButton.tsx`: 클립보드 복사 버튼 구현
    - 전체 대화 내용을 텍스트로 변환하여 클립보드에 복사
    - 복사 완료 시 2초간 "복사됨" 피드백 표시
    - messages가 없거나 isStreaming 상태일 때 비활성화
    - _요구사항: 5.1, 5.2, 5.3, 5.4_

- [ ] 9. 법령 파싱 서비스 및 관리자 라우터 구현
  - [ ] 9.1 법령 파싱 서비스 구현
    - `backend/app/services/law_parser_service.py`: LawParserService 클래스 구현
    - `extract_text_from_pdf(pdf_path)`: pdfplumber로 전체 페이지 텍스트 추출, 헤더/푸터 제거
    - `split_into_chunks(text)`: 정규식 `r'제\d+조\s*\([^)]+\)'`로 조 단위 분할
    - `parse_chunk_with_gpt(chunk)`: OpenAIService.parse_law_structure()로 청크 구조화 파싱
    - `validate_and_save(db, articles)`: Pydantic ArticleSchema 검증 후 트랜잭션으로 DB 저장 (기존 데이터 전체 삭제 후 INSERT, 실패 시 ROLLBACK)
    - _요구사항: 6.2, 6.3, 1.7 (트랜잭션 롤백)_

  - [ ] 9.2 POST /admin/parse-law 엔드포인트 구현
    - `backend/app/routers/admin.py`: POST /admin/parse-law 엔드포인트 구현
    - X-Admin-Key 헤더 검증: 없거나 ADMIN_SECRET_KEY 불일치 시 HTTP 401 + UNAUTHORIZED 반환
    - LawParserService.validate_and_save() 호출
    - 성공 시 ParseLawResponse(stats: articles/paragraphs/subparagraphs/items 수, processed_at) 반환
    - 파싱 오류 시 HTTP 500 + PARSE_ERROR 반환
    - _요구사항: 6.1, 6.4, 6.5, 6.6, 1.7_

  - [ ]* 9.3 관리자 인증 키 속성 기반 테스트 작성
    - **Property 7: 관리자 인증 키 검증**
    - **Validates: Requirements 6.4, 6.5**
    - `backend/tests/test_admin.py`: hypothesis로 임의의 잘못된 키 또는 빈 헤더에 대해 항상 HTTP 401 반환 검증
    - 올바른 키 제공 시에만 파싱 로직 실행 검증 (LawParserService 모킹)

  - [ ]* 9.4 법령 파싱 라운드트립 속성 기반 테스트 작성
    - **Property 6: 법령 파싱 라운드트립**
    - **Validates: Requirements 6.2, 6.3**
    - `backend/tests/test_law_parser.py`: hypothesis로 임의의 유효한 법령 텍스트 청크 파싱 후 DB 저장 및 재조회 시 원본 조항 번호와 내용 보존 검증

- [ ] 10. 체크포인트 - 백엔드 테스트 통과 확인
  - 모든 백엔드 테스트가 통과하는지 확인한다. 문제가 있으면 사용자에게 질문한다.

- [ ] 11. TypeScript 타입 정의 및 API 클라이언트 구현
  - [ ] 11.1 TypeScript 타입 정의
    - `frontend/src/types/index.ts`: MessageRole, ComplianceStatus, Priority, ComplianceItem, ComplianceData, ChatMessage, ChatSession 타입 정의
    - _요구사항: 2.2, 3.2, 4.1_

  - [ ] 11.2 API 클라이언트 구현
    - `frontend/src/api/client.ts`: sendChatMessage(url, body), exportPDF(messages, projectSummary) 함수 구현
    - fetch API 기반, VITE_API_BASE_URL 환경변수 사용
    - _요구사항: 1.1, 5.1_

- [ ] 12. 프론트엔드 커스텀 훅 구현
  - [ ] 12.1 useSSE 훅 구현
    - `frontend/src/hooks/useSSE.ts`: fetch API + ReadableStream으로 SSE 처리
    - onChunk(chunk), onDone(complianceData), onError(error) 콜백 지원
    - EventSource 대신 fetch 사용 (POST body 전송 필요)
    - _요구사항: 1.2 (500ms 이내 수신 확인), 2.4 (30초 이내 응답)_

  - [ ] 12.2 useChatSession 훅 구현
    - `frontend/src/hooks/useChatSession.ts`: 세션 상태 관리 구현
    - sessionStorage 키 "chat_session"으로 ChatSession 저장/복원
    - lastActiveAt 기준 30분 초과 시 세션 만료 처리 및 새 세션 생성
    - sendMessage(content): useSSE로 POST /api/chat 호출, 스트리밍 청크 누적, done 이벤트 시 compliance_data 저장
    - exportPDF(): POST /api/chat/export-pdf 호출, PDF 다운로드 트리거
    - clearSession(): sessionStorage 초기화 및 새 세션 생성
    - _요구사항: 4.1, 4.2, 4.3, 5.1_

  - [ ]* 12.3 세션 만료 감지 속성 기반 테스트 작성
    - **Property 4: 세션 만료 감지**
    - **Validates: Requirements 4.3**
    - `frontend/src/hooks/useChatSession.test.ts`: vitest + hypothesis 스타일로 lastActiveAt 기준 30분 초과 세션은 항상 만료 상태, 30분 미만은 항상 활성 상태 검증

- [ ] 13. 프론트엔드 UI 컴포넌트 구현
  - [ ] 13.1 폰트 설정 및 Tailwind 기반 스타일 구현
    - `frontend/src/styles/index.css`: @font-face 선언 (KBFGDisplay Light/Medium, KBFGText Light/Medium/Bold)
    - `frontend/tailwind.config.ts`: fontFamily.display = KBFGDisplay, fontFamily.sans = KBFGText 등록
    - _요구사항: 8.1 (웹 인터페이스)_

  - [ ] 13.2 DisclaimerBanner 컴포넌트 구현
    - `frontend/src/components/DisclaimerBanner.tsx`: 면책 조항 상단 고정 배너 구현
    - "본 결과는 참고용이며, 법적 효력이 없습니다. 정확한 법률 해석은 전문가에게 문의하세요." 문구 표시
    - _요구사항: 2.1 (법적 조언 아님 명시), 제약사항 2.1_

  - [ ] 13.3 MessageBubble 및 ComplianceCard 컴포넌트 구현
    - `frontend/src/components/MessageBubble.tsx`: role에 따라 좌(assistant)/우(user) 정렬 버블 구현
    - compliance_data 존재 시 ComplianceCard 렌더링 (전체 등급, 항목별 status/priority/recommendation)
    - _요구사항: 8.3 (사용자/챗봇 메시지 시각적 구분), 2.2, 3.1_

  - [ ] 13.4 MessageList 컴포넌트 구현
    - `frontend/src/components/MessageList.tsx`: messages 배열을 timestamp 오름차순으로 렌더링
    - MessageBubble 목록 렌더링, 새 메시지 추가 시 자동 스크롤
    - _요구사항: 8.3 (대화 내역 시간순 표시)_

  - [ ]* 13.5 메시지 순서 보존 테스트 작성
    - **Property 9: 메시지 순서 보존**
    - **Validates: Requirements 8.3**
    - `frontend/src/components/MessageList.test.tsx`: 임의 순서의 메시지 배열 입력 시 항상 timestamp 오름차순으로 렌더링됨 검증

  - [ ] 13.6 InputBar 컴포넌트 구현
    - `frontend/src/components/InputBar.tsx`: 텍스트 입력 + 전송 버튼 구현
    - 5,000자 초과 입력 시 클라이언트 측 경고 표시 및 전송 차단
    - isStreaming 상태일 때 입력 및 전송 버튼 비활성화
    - Enter 키 전송 지원 (Shift+Enter는 줄바꿈)
    - _요구사항: 1.1, 1.3, 1.4, 8.4_

  - [ ]* 13.7 InputBar 5000자 초과 입력 차단 테스트 작성
    - **Property 1 (프론트엔드): 입력 길이 경계 검증**
    - **Validates: Requirements 1.3, 1.4**
    - `frontend/src/components/InputBar.test.tsx`: 5001자 이상 입력 시 전송 버튼 비활성화 및 경고 표시 검증

  - [ ] 13.8 LoadingIndicator 컴포넌트 구현
    - `frontend/src/components/LoadingIndicator.tsx`: isStreaming 상태일 때 표시되는 로딩 인디케이터 구현
    - _요구사항: 8.4 (분석 중 로딩 인디케이터)_

  - [ ] 13.9 ExportButton 컴포넌트 구현
    - `frontend/src/components/ExportButton.tsx`: PDF 내보내기 버튼 구현
    - useChatSession.exportPDF() 호출, 로딩 상태 표시
    - messages가 없거나 isStreaming 상태일 때 비활성화
    - _요구사항: 5.1, 5.2_

  - [ ] 13.10 ChatWindow 컴포넌트 구현
    - `frontend/src/components/ChatWindow.tsx`: 전체 채팅 레이아웃 구현
    - DisclaimerBanner, MessageList, LoadingIndicator, InputBar, ExportButton 조합
    - useChatSession 훅 연결
    - 데스크톱(1280px 이상) 및 태블릿(768px 이상) 반응형 레이아웃
    - _요구사항: 8.1, 8.2, 8.3, 8.4_

  - [ ] 13.11 App.tsx 및 main.tsx 진입점 구현
    - `frontend/src/App.tsx`: ChatWindow 렌더링
    - `frontend/src/main.tsx`: React 앱 마운트, index.css 임포트
    - `frontend/index.html`: Vite 진입점 HTML
    - _요구사항: 8.1_

- [ ] 14. 응답 구조 완전성 및 개선 권고사항 구조 테스트 작성
  - [ ]* 14.1 응답 구조 완전성 속성 기반 테스트 작성
    - **Property 2: 응답 구조 완전성**
    - **Validates: Requirements 2.2, 2.3**
    - `backend/tests/test_chat.py`: hypothesis로 임의의 유효한 AI 프로젝트 설명에 대해 응답에 항상 전체 준수 등급, 관련 조항 번호, 면책 조항 포함 검증 (OpenAI 모킹)

  - [ ]* 14.2 개선 권고사항 구조 완전성 속성 기반 테스트 작성
    - **Property 3: 개선 권고사항 구조 완전성**
    - **Validates: Requirements 3.1, 3.2, 3.3**
    - `backend/tests/test_chat.py`: hypothesis로 미준수/부분 준수 항목 포함 분석 결과에 항상 우선순위, 개선 권고사항, 관련 조항 요약 포함 검증

- [ ] 15. 최종 체크포인트 - 전체 테스트 통과 확인
  - 백엔드 및 프론트엔드 모든 테스트가 통과하는지 확인한다. 문제가 있으면 사용자에게 질문한다.

- [ ] 16. 가이드라인 임베딩 및 법령 연관 태깅 구현
  - [x] 16.1 guideline_chunks ORM 모델 추가
    - `backend/app/models/law.py`에 GuidelineChunk 클래스 추가
    - source, page_no, content, vector, model, related_articles, created_at 필드
    - _요구사항: 9.1, 9.2_

  - [x] 16.2 GuidelineService 구현
    - `backend/app/services/guideline_service.py`: 텍스트 추출 가능 PDF 처리
    - pdfplumber로 페이지 단위 텍스트 추출 → 임베딩 → guideline_chunks 저장
    - _요구사항: 9.2_

  - [x] 16.3 OCRService 구현
    - `backend/app/services/ocr_service.py`: 스캔본 PDF OCR 처리
    - pymupdf로 페이지 이미지 변환 → GPT-4o Vision OCR → 임베딩 저장
    - _요구사항: 9.3_

  - [x] 16.4 관리자 엔드포인트 추가
    - `POST /admin/embed-guideline`: 텍스트 추출 가능 PDF 임베딩
    - `POST /admin/embed-guideline-ocr`: 스캔본 PDF OCR + 임베딩
    - _요구사항: 9.1, 9.2, 9.3_

  - [ ] 16.5 가이드라인 법령 조항 자동 태깅 구현
    - `backend/app/services/guideline_service.py`에 `tag_all_chunks(db)` 메서드 추가
    - 각 청크를 GPT-4o mini에 전달하여 관련 조항 번호 추출
    - `related_articles` 필드에 JSON 배열로 저장
    - `POST /admin/tag-guidelines` 엔드포인트 추가
    - _요구사항: 9.4, 9.5_

  - [ ] 16.6 태그 기반 RAG 검색 통합
    - `backend/app/services/rag_service.py` 수정
    - 법령 조항 검색 결과의 조항 번호로 related_articles 필터링
    - 태그된 가이드라인 청크 우선 반환, 없으면 임베딩 유사도 폴백
    - _요구사항: 9.6, 9.7_

---

## 참고사항

- `*` 표시 태스크는 선택적이며 MVP 구현 시 건너뛸 수 있다.
- 각 태스크는 이전 태스크를 기반으로 순차적으로 구현한다.
- 체크포인트에서 테스트 실패 시 해당 태스크로 돌아가 수정한다.
- 속성 기반 테스트는 hypothesis 라이브러리를 사용하며, 각 속성은 최소 100회 이상 실행된다.
- 단위 테스트는 pytest + pytest-asyncio, 프론트엔드 테스트는 vitest + @testing-library/react를 사용한다.

- [ ] 17. 관리자 대화 로그 대시보드 구현
  - [x] 17.1 출력 형식 및 가드레일 시스템 프롬프트 적용
    - `backend/app/services/rag_service.py`: 관련 법령 / 관련 가이드라인 / 권장 액션 3섹션 출력 형식 강제
    - AI 기본법 무관 질문 거절 가드레일 추가
    - _요구사항: 2.4, 2.8_

  - [ ] 17.2 대화 로그 DB 모델 및 저장 로직 구현
    - `backend/app/models/log.py`: ConversationLog 모델 (session_id, first_question, messages JSON, created_at)
    - `backend/app/routers/chat.py`: 대화 완료 시 로그 저장
    - _요구사항: 10.1_

  - [ ] 17.3 관리자 로그 API 엔드포인트 구현
    - `GET /admin/logs`: 세션 목록 반환 (X-Admin-Key 인증)
    - `GET /admin/logs/{session_id}`: 특정 세션 전체 대화 반환
    - _요구사항: 10.2, 10.3_

  - [ ] 17.4 관리자 대시보드 프론트엔드 구현
    - `frontend/src/pages/AdminDashboard.tsx`: 세션 목록 + 대화 상세 화면
    - `/admin/logs` 경로로 접근, X-Admin-Key 입력 인증
    - _요구사항: 10.4, 10.5, 10.6, 10.7_
