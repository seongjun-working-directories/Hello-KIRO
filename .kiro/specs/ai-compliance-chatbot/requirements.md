# Requirements Document

## Introduction

AI 기본법(한국 인공지능 기본법) 준수 여부를 확인해주는 챗봇 서비스입니다.
개발자 및 기획자가 자신의 AI 프로젝트 아이디어를 입력하면, 챗봇이 AI 기본법 주요 조항과 대조하여 준수 여부를 분석하고 개선 권고사항을 제공합니다.
백엔드는 Python, 프론트엔드는 React 기반의 웹 서비스로 구현됩니다.

## Glossary

- **Chatbot**: 사용자와 대화형 인터페이스를 통해 AI 기본법 준수 여부를 분석하는 시스템
- **User**: 챗봇 서비스를 이용하여 AI 프로젝트 아이디어를 검토받는 개발자 또는 기획자
- **AI_Project**: 사용자가 개발하고자 하는 AI 기반 서비스 또는 시스템
- **Compliance_Report**: AI 기본법 준수 여부 분석 결과를 담은 응답 (준수/부분 준수/미준수 등급 포함)
- **Session**: 사용자와 챗봇 간의 단일 대화 세션
- **LLM_Backend**: 자연어 처리 및 법률 분석을 수행하는 대형 언어 모델 백엔드

## Requirements

### Requirement 1: 대화형 프로젝트 아이디어 입력

**User Story:** As a developer, I want to describe my AI project idea to the chatbot in free-form text, so that I can get a compliance review without filling out a structured form.

#### Acceptance Criteria

1. THE Chatbot SHALL 사용자가 자유 텍스트 형식으로 AI 프로젝트 아이디어를 입력할 수 있는 대화 인터페이스를 제공한다.
2. WHEN 사용자가 메시지를 전송하면, THE Chatbot SHALL 500ms 이내에 입력 수신 확인 응답을 반환한다.
3. THE Chatbot SHALL 단일 메시지 기준 최대 5,000자의 입력을 처리한다.
4. IF 입력이 5,000자를 초과하면, THEN THE Chatbot SHALL 입력 길이 초과 안내 메시지를 반환한다.

### Requirement 2: AI 기본법 준수 여부 분석

**User Story:** As a developer, I want my project idea to be automatically analyzed against the Korean AI Act, so that I can identify legal risks before development.

#### Acceptance Criteria

1. WHEN 사용자가 AI 프로젝트 아이디어를 입력하면, THE LLM_Backend SHALL AI 기본법의 주요 조항과 대조하여 준수 여부를 분석한다.
2. THE Chatbot SHALL 분석 결과를 준수(Compliant), 부분 준수(Partially Compliant), 미준수(Non-Compliant) 세 가지 등급으로 분류하여 반환한다.
3. THE Chatbot SHALL 각 분석 항목에 대해 관련 AI 기본법 조항 번호를 명시한다.
4. WHEN 분석이 완료되면, THE Chatbot SHALL 30초 이내에 Compliance_Report를 사용자에게 반환한다.
5. IF LLM_Backend가 응답하지 않으면, THEN THE Chatbot SHALL 오류 메시지와 함께 재시도 안내를 제공한다.

### Requirement 3: 개선 권고사항 제공

**User Story:** As a developer, I want to receive specific improvement suggestions for non-compliant items, so that I can revise my project to meet legal requirements.

#### Acceptance Criteria

1. WHEN Compliance_Report에 미준수 또는 부분 준수 항목이 존재하면, THE Chatbot SHALL 각 항목에 대한 구체적인 개선 권고사항을 제공한다.
2. THE Chatbot SHALL 개선 권고사항을 우선순위(높음/중간/낮음)와 함께 제시한다.
3. THE Chatbot SHALL 개선 권고사항에 관련 AI 기본법 조항의 요약 설명을 포함한다.

### Requirement 4: 대화 맥락 유지 (멀티턴 대화)

**User Story:** As a developer, I want to ask follow-up questions based on previous conversation, so that I can have an in-depth discussion about the analysis results.

#### Acceptance Criteria

1. WHILE Session이 활성 상태인 동안, THE Chatbot SHALL 이전 대화 내용을 컨텍스트로 유지하여 후속 질문에 응답한다.
2. THE Chatbot SHALL 단일 Session 내에서 최소 20회의 대화 턴을 지원한다.
3. WHEN Session이 30분 이상 비활성 상태가 되면, THE Chatbot SHALL 세션 만료를 안내하고 새 세션 시작을 유도한다.

### Requirement 5: 분석 결과 내보내기

**User Story:** As a developer, I want to export the analysis results as a document, so that I can share them with my team or keep them as a record.

#### Acceptance Criteria

1. THE Chatbot SHALL 사용자가 Compliance_Report를 PDF 또는 Markdown 형식으로 내보낼 수 있는 기능을 제공한다.
2. WHEN 사용자가 내보내기를 요청하면, THE Chatbot SHALL 10초 이내에 다운로드 가능한 파일을 생성한다.
3. THE Chatbot SHALL 내보낸 파일에 분석 일시, 프로젝트 요약, 준수 등급, 개선 권고사항을 포함한다.

### Requirement 6: 사용자 인터페이스

**User Story:** As a developer, I want an intuitive web interface, so that I can use the chatbot without any learning curve.

#### Acceptance Criteria

1. THE Chatbot SHALL React 기반의 웹 인터페이스를 통해 접근 가능하다.
2. THE Chatbot SHALL 데스크톱(1280px 이상) 및 태블릿(768px 이상) 화면 크기를 지원한다.
3. THE Chatbot SHALL 대화 내역을 시간순으로 표시하며, 사용자 메시지와 챗봇 응답을 시각적으로 구분한다.
4. WHEN 분석이 진행 중인 동안, THE Chatbot SHALL 로딩 인디케이터를 표시한다.
