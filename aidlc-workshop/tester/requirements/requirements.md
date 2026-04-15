# 기능 요구사항 (Requirements)

## 소개

본 문서는 AI 기본법(한국 인공지능 기본법) 준수 여부를 확인해주는 챗봇 서비스의 기능 요구사항을 정의합니다.
사용자는 자신의 AI 프로젝트 아이디어를 입력하고, 챗봇은 해당 아이디어가 AI 기본법의 주요 조항을 준수하는지 분석하여 피드백을 제공합니다.

## 용어 정의 (Glossary)

- **Chatbot**: 사용자와 대화형 인터페이스를 통해 AI 기본법 준수 여부를 분석하는 시스템
- **User**: 챗봇 서비스를 이용하여 자신의 AI 프로젝트 아이디어를 검토받는 개발자 또는 기획자
- **AI_Project**: 사용자가 개발하고자 하는 AI 기반 서비스 또는 시스템
- **Compliance_Report**: AI 기본법 준수 여부 분석 결과를 담은 응답
- **Session**: 사용자와 챗봇 간의 단일 대화 세션
- **LLM_Backend**: OpenAI의 GPT-4o mini 모델을 사용하여 자연어 처리 및 법률 분석을 수행하는 대형 언어 모델 백엔드
- **GPT4o_Mini**: OpenAI에서 제공하는 대형 언어 모델로, 본 서비스의 AI 분석 엔진으로 사용됨. 한국어 성능과 Python SDK 성숙도가 높으며, 질문당 약 1~3원 수준의 비용이 발생함
- **Rate_Limiter**: 동일 IP의 과도한 요청을 제한하는 시스템 컴포넌트
- **RAG_Pipeline**: 사용자 질문을 임베딩 기반으로 관련 법령 조항을 검색하고 GPT 프롬프트에 컨텍스트로 제공하는 파이프라인
- **Query_Expansion**: 사용자 입력에서 법적 쟁점 키워드를 GPT로 추출하여 검색 정확도를 높이는 전처리 단계
- **Embedding**: OpenAI text-embedding-3-small 모델을 사용하여 텍스트를 벡터로 변환하는 과정
- **Vector_Search**: 임베딩 벡터 간 코사인 유사도를 계산하여 의미적으로 가장 관련성 높은 조항을 검색하는 방식
- **Admin_Endpoint**: AI 기본법 파싱, 임베딩 생성 및 DB 초기화를 위한 관리자 전용 REST API 엔드포인트

---

## 요구사항 목록

### 요구사항 1: 대화형 프로젝트 아이디어 입력

**User Story:** 개발자로서, 나는 챗봇에게 내 AI 프로젝트 아이디어를 자유로운 형식으로 설명하고 싶다. 그래야 별도의 양식 없이 편리하게 검토를 받을 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE Chatbot SHALL 사용자가 자유 텍스트 형식으로 AI 프로젝트 아이디어를 입력할 수 있는 대화 인터페이스를 제공한다.
2. WHEN 사용자가 메시지를 전송하면, THE Chatbot SHALL 500ms 이내에 입력 수신 확인 응답을 반환한다.
3. THE Chatbot SHALL 단일 메시지 기준 최대 5,000자의 입력을 처리한다.
4. IF 입력이 5,000자를 초과하면, THEN THE Chatbot SHALL 입력 길이 초과 안내 메시지를 반환한다.

---

### 요구사항 2: AI 기본법 준수 여부 분석

**User Story:** 개발자로서, 나는 내 프로젝트 아이디어가 AI 기본법의 주요 조항을 준수하는지 자동으로 분석받고 싶다. 그래야 법적 리스크를 사전에 파악할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. WHEN 사용자가 AI 프로젝트 아이디어를 입력하면, THE System SHALL Query_Expansion 단계를 통해 입력에서 법적 쟁점 키워드를 추출한다.
2. THE System SHALL 추출된 키워드를 임베딩하여 SQLite에 저장된 법령 조항 벡터와 코사인 유사도를 계산하고 상위 5개 관련 조항을 검색한다.
3. WHEN 관련 조항이 검색되면, THE GPT4o_Mini SHALL 해당 조항을 컨텍스트로 포함하여 준수 여부를 분석한다.
4. THE Chatbot SHALL 분석 결과를 반드시 다음 세 섹션으로 구분하여 반환한다: **관련 법령** / **관련 가이드라인** / **권장 액션**
5. THE Chatbot SHALL 각 분석 항목에 대해 관련 AI 기본법 조항 번호를 명시한다.
6. WHEN 분석이 완료되면, THE Chatbot SHALL 30초 이내에 Compliance_Report를 사용자에게 반환한다.
7. IF GPT4o_Mini가 응답하지 않으면, THEN THE Chatbot SHALL 오류 메시지와 함께 재시도 안내를 제공한다.
8. IF 사용자 입력이 AI 기본법과 무관한 질문인 경우, THEN THE Chatbot SHALL 답변을 거절하고 AI 기본법 관련 질문을 유도하는 안내 메시지를 반환한다.

---

### 요구사항 3: 개선 권고사항 제공

**User Story:** 개발자로서, 나는 미준수 항목에 대한 구체적인 개선 방향을 제안받고 싶다. 그래야 프로젝트를 법적으로 적합하게 수정할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. WHEN Compliance_Report에 미준수 또는 부분 준수 항목이 존재하면, THE Chatbot SHALL 각 항목에 대한 구체적인 개선 권고사항을 제공한다.
2. THE Chatbot SHALL 개선 권고사항을 우선순위(높음/중간/낮음)와 함께 제시한다.
3. THE Chatbot SHALL 개선 권고사항에 관련 AI 기본법 조항의 요약 설명을 포함한다.

---

### 요구사항 4: 대화 맥락 유지 (멀티턴 대화)

**User Story:** 개발자로서, 나는 이전 대화 내용을 기반으로 후속 질문을 할 수 있기를 원한다. 그래야 분석 결과에 대해 심층적으로 논의할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. WHILE Session이 활성 상태인 동안, THE Chatbot SHALL 이전 대화 내용을 컨텍스트로 유지하여 후속 질문에 응답한다.
2. THE Chatbot SHALL 단일 Session 내에서 최소 20회의 대화 턴을 지원한다.
3. WHEN Session이 30분 이상 비활성 상태가 되면, THE Chatbot SHALL 세션 만료를 안내하고 새 세션 시작을 유도한다.

---

### 요구사항 5: 분석 결과 복사

**User Story:** 개발자로서, 나는 분석 결과 전체를 클립보드에 복사하고 싶다. 그래야 팀원들과 결과를 공유하거나 문서에 붙여넣을 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE Chatbot SHALL 사용자가 대화 내용 전체를 클립보드에 복사할 수 있는 버튼을 제공한다.
2. WHEN 사용자가 복사 버튼을 클릭하면, THE Chatbot SHALL 전체 대화 내용을 텍스트 형식으로 클립보드에 복사한다.
3. THE Chatbot SHALL 복사 완료 시 "복사됨" 피드백을 2초간 표시한다.
4. THE Chatbot SHALL 복사되는 텍스트에 분석 일시, 사용자 질문, AI 분석 결과, 면책 조항을 포함한다.

---

### 요구사항 6: AI 기본법 파싱, 임베딩 및 DB 초기화

**User Story:** 서비스 관리자로서, 나는 특정 API 엔드포인트를 호출하여 AI 기본법 원문을 파싱하고 임베딩을 생성하여 DB에 저장하고 싶다. 그래야 법령 개정 시 별도의 스크립트 없이 서비스 내에서 DB를 갱신할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE System SHALL `POST /admin/parse-law` 엔드포인트를 제공한다.
2. WHEN 해당 엔드포인트가 호출되면, THE System SHALL 프로젝트 루트에 위치한 AI 기본법 원문 파일을 읽어 GPT-4o mini API를 통해 조→항→호→목 계층 구조로 파싱한다.
3. THE System SHALL 파싱 결과를 SQLite DB에 저장(기존 데이터 덮어쓰기)한다.
4. WHEN 파싱이 완료되면, THE System SHALL `POST /admin/embed-law` 엔드포인트를 통해 각 조항의 텍스트를 OpenAI text-embedding-3-small 모델로 임베딩하여 SQLite DB에 저장한다.
5. THE System SHALL 해당 엔드포인트 호출 시 요청 헤더의 `X-Admin-Key` 값을 환경변수 `ADMIN_SECRET_KEY`와 대조하여 인증한다.
6. IF `X-Admin-Key`가 없거나 일치하지 않으면, THEN THE System SHALL HTTP 401 상태 코드를 반환한다.
7. WHEN 파싱 및 임베딩이 완료되면, THE System SHALL 저장된 조항 수와 처리 결과를 JSON으로 반환한다.

---

### 요구사항 9: AI 가이드라인 임베딩 및 법령 연관 태깅

**User Story:** 서비스 관리자로서, 나는 AI 기본법 관련 가이드라인 문서를 임베딩하고 각 가이드라인 청크가 어떤 법령 조항과 관련되는지 자동으로 태깅하고 싶다. 그래야 사용자 질문에 대해 법령 조항과 구체적인 행동 원칙을 함께 제시할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE System SHALL `POST /admin/embed-guideline` 엔드포인트를 제공한다.
2. WHEN 해당 엔드포인트가 호출되면, THE System SHALL `data/guidelines/` 폴더의 PDF 파일들을 페이지 단위로 청크화하여 임베딩 후 `guideline_chunks` 테이블에 저장한다.
3. THE System SHALL 텍스트 추출이 불가능한 스캔본 PDF에 대해 `POST /admin/embed-guideline-ocr` 엔드포인트를 통해 GPT-4o Vision으로 OCR 처리 후 임베딩을 저장한다.
4. THE System SHALL `POST /admin/tag-guidelines` 엔드포인트를 제공한다.
5. WHEN 해당 엔드포인트가 호출되면, THE System SHALL 각 가이드라인 청크를 GPT-4o mini에 전달하여 관련 AI 기본법 조항 번호를 추출하고 `related_articles` 필드에 저장한다.
6. WHEN 사용자가 질문을 입력하면, THE System SHALL 임베딩 유사도로 법령 조항을 검색하고, 해당 조항과 태그된 가이드라인 청크를 우선적으로 함께 GPT에 전달한다.
7. THE Chatbot SHALL 응답에 관련 법령 조항과 가이드라인 출처를 함께 명시한다.

---

### 요구사항 7: IP 기반 Rate Limiting

**User Story:** 서비스 운영자로서, 나는 동일 IP에서의 과도한 요청을 제한하고 싶다. 그래야 서비스 남용을 방지하고 모든 사용자에게 안정적인 서비스를 제공할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE Rate_Limiter SHALL 동일 IP 주소에서 10분 이내에 전송된 질문 수를 추적한다.
2. WHEN 동일 IP 주소에서 10분 이내에 5개 이상의 질문이 전송되면, THE Rate_Limiter SHALL 해당 요청을 차단하고 안내 메시지를 반환한다.
3. THE Chatbot SHALL Rate Limiting 초과 시 "요청 한도를 초과했습니다. 10분 후에 다시 시도해주세요."라는 안내 메시지를 반환한다.
4. WHEN 제한 시간(10분)이 경과하면, THE Rate_Limiter SHALL 해당 IP의 요청 카운터를 초기화한다.

---

### 요구사항 8: 사용자 인터페이스

**User Story:** 개발자로서, 나는 직관적인 웹 인터페이스를 통해 챗봇을 사용하고 싶다. 그래야 별도의 학습 없이 바로 서비스를 이용할 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE Chatbot SHALL React 기반의 웹 인터페이스를 통해 접근 가능하다.
2. THE Chatbot SHALL 데스크톱(1280px 이상) 및 태블릿(768px 이상) 화면 크기를 지원한다.
3. THE Chatbot SHALL 대화 내역을 시간순으로 표시하며, 사용자 메시지와 챗봇 응답을 시각적으로 구분한다.
4. THE Chatbot SHALL 사용자 메시지 옆에 전송 시각을 YY/MM/DD HH:MM 형식으로 표시한다.
5. WHEN 분석이 진행 중인 동안, THE Chatbot SHALL 로딩 인디케이터를 표시한다.

---

### 요구사항 10: 관리자 대화 로그 대시보드

**User Story:** 서비스 관리자로서, 나는 사용자들이 어떤 질문을 했는지 대화 내역을 조회하고 싶다. 그래야 서비스 이용 현황을 파악하고 개선점을 찾을 수 있다.

#### 수용 기준 (Acceptance Criteria)

1. THE System SHALL 사용자의 각 대화 세션을 서버에 저장한다. (세션 ID, 첫 번째 질문, 전체 대화 내역, 시작 시각)
2. THE System SHALL `GET /admin/logs` 엔드포인트를 제공하며, `X-Admin-Key` 인증 후 세션 목록을 반환한다.
3. THE System SHALL `GET /admin/logs/{session_id}` 엔드포인트를 제공하며, 특정 세션의 전체 대화 내역을 반환한다.
4. THE System SHALL 관리자 대시보드 페이지(`/admin/logs`)를 제공한다.
5. THE Dashboard SHALL 세션 목록을 최초 질문 내용과 시작 시각 기준으로 최신순으로 표시한다.
6. WHEN 관리자가 목록의 세션을 클릭하면, THE Dashboard SHALL 해당 세션의 전체 대화 내역을 표시한다.
7. THE Dashboard SHALL 대화 상세 화면에서 사용자 메시지 옆에 전송 시각을 YY/MM/DD HH:MM 형식으로 표시한다.
8. THE Dashboard SHALL `X-Admin-Key` 입력 화면을 통해 인증 후 접근 가능하다.
9. WHEN 관리자가 세션 목록에서 X 버튼을 클릭하면, THE System SHALL 해당 세션의 로그를 삭제한다.
