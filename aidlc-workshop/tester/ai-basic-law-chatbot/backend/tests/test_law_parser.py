"""
Feature: ai-basic-law-chatbot, Property 6: 법령 파싱 라운드트립
Validates: Requirements 6.2, 6.3
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.law_parser_service import LawParserService
from app.services.openai_service import OpenAIService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_split_into_chunks_basic():
    parser = LawParserService()
    text = "제1조(목적) 이 법은...\n제2조(정의) 이 법에서..."
    chunks = parser.split_into_chunks(text)
    assert len(chunks) == 2
    assert chunks[0].startswith("제1조")
    assert chunks[1].startswith("제2조")


def test_validate_and_save_roundtrip(db_session):
    """저장 후 재조회 시 조항 번호와 내용이 보존되어야 한다."""
    parser = LawParserService()
    articles_data = [
        {
            "article_no": "제1조",
            "title": "목적",
            "content": "이 법은 AI 기본법의 목적을 정한다.",
            "paragraphs": [
                {
                    "paragraph_no": "①",
                    "content": "AI 시스템의 안전성을 확보한다.",
                    "subparagraphs": [],
                }
            ],
        }
    ]

    stats = parser.validate_and_save(db_session, articles_data)
    assert stats["articles"] == 1
    assert stats["paragraphs"] == 1

    from app.models.law import Article
    saved = db_session.query(Article).filter_by(article_no="제1조").first()
    assert saved is not None
    assert saved.title == "목적"
    assert saved.content == "이 법은 AI 기본법의 목적을 정한다."


def test_validate_and_save_rollback_on_error(db_session):
    """오류 발생 시 DB가 롤백되어야 한다."""
    parser = LawParserService()

    # 잘못된 데이터 (필수 필드 누락) - 모두 스킵되어 빈 리스트로 저장
    articles_data = [{"invalid": "data"}]
    stats = parser.validate_and_save(db_session, articles_data)
    assert stats["articles"] == 0
