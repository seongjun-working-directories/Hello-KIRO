"""
임베딩 서비스 및 RAG 파이프라인 테스트
- EmbeddingService: 벡터 저장/검색
- RAGService: Query Expansion + 임베딩 검색 + LIKE 폴백
"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.law import Article, Paragraph, Embedding
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_article(db_session):
    """테스트용 조항 데이터."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    article = Article(
        article_no="제22조",
        title="고위험 AI 시스템",
        content="고위험 AI 시스템은 다음 요건을 갖춰야 한다.",
        created_at=now,
    )
    db_session.add(article)
    db_session.flush()
    para = Paragraph(
        article_id=article.id,
        paragraph_no="①",
        content="생체정보 처리 시 명시적 동의를 받아야 한다.",
        created_at=now,
    )
    db_session.add(para)
    db_session.commit()
    return article


# --- EmbeddingService 단위 테스트 ---

def test_cosine_similarity_identical_vectors():
    """동일 벡터의 코사인 유사도는 1.0이어야 한다."""
    svc = EmbeddingService.__new__(EmbeddingService)
    v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    v_norm = v / np.linalg.norm(v)
    score = float(np.dot(v_norm, v_norm))
    assert abs(score - 1.0) < 1e-5


def test_cosine_similarity_orthogonal_vectors():
    """직교 벡터의 코사인 유사도는 0에 가까워야 한다."""
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    score = float(np.dot(v1, v2))
    assert abs(score) < 1e-5


def test_search_by_vector_returns_top_k(db_session, sample_article):
    """벡터 검색이 상위 k개 조항을 반환해야 한다."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    # 임베딩 저장
    vector = np.random.rand(1536).astype(np.float32)
    db_session.add(Embedding(
        article_id=sample_article.id,
        vector=vector.tobytes(),
        model="text-embedding-3-small",
        created_at=now,
    ))
    db_session.commit()

    svc = EmbeddingService.__new__(EmbeddingService)
    results = svc.search_by_vector(db_session, vector, top_k=5)
    assert len(results) == 1
    assert results[0]["article_no"] == "제22조"


def test_search_by_vector_empty_db(db_session):
    """임베딩이 없으면 빈 리스트를 반환해야 한다."""
    svc = EmbeddingService.__new__(EmbeddingService)
    query = np.random.rand(1536).astype(np.float32)
    results = svc.search_by_vector(db_session, query, top_k=5)
    assert results == []


@pytest.mark.anyio
async def test_embed_all_articles(db_session, sample_article):
    """embed_all_articles가 조항 수만큼 임베딩을 저장해야 한다."""
    fake_vector = np.random.rand(1536).astype(np.float32)

    with patch.object(EmbeddingService, "create_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = fake_vector
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.client = MagicMock()
        svc.create_embedding = mock_embed

        stats = await svc.embed_all_articles(db_session)

    assert stats["embedded"] == 1
    assert stats["failed"] == 0
    saved = db_session.query(Embedding).filter_by(article_id=sample_article.id).first()
    assert saved is not None


# --- RAGService 단위 테스트 ---

@pytest.mark.anyio
async def test_rag_falls_back_to_keyword_when_no_embeddings(db_session, sample_article):
    """임베딩이 없으면 LIKE 검색으로 폴백해야 한다."""
    rag = RAGService(db_session)
    articles, guidelines = await rag.search_relevant_articles("고위험 AI 시스템")
    assert len(articles) >= 1
    assert articles[0]["article_no"] == "제22조"


@pytest.mark.anyio
async def test_rag_uses_embedding_when_available(db_session, sample_article):
    """임베딩이 있으면 벡터 검색을 사용해야 한다."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    vector = np.random.rand(1536).astype(np.float32)
    db_session.add(Embedding(
        article_id=sample_article.id,
        vector=vector.tobytes(),
        model="text-embedding-3-small",
        created_at=now,
    ))
    db_session.commit()

    rag = RAGService(db_session)

    with patch.object(RAGService, "expand_query", new_callable=AsyncMock) as mock_expand, \
         patch.object(EmbeddingService, "create_embedding", new_callable=AsyncMock) as mock_embed:
        mock_expand.return_value = ["고위험AI", "생체정보"]
        mock_embed.return_value = vector

        articles, guidelines = await rag.search_relevant_articles("얼굴 인식 시스템")

    assert len(articles) >= 1
    assert articles[0]["article_no"] == "제22조"


@pytest.mark.anyio
async def test_query_expansion_failure_falls_back_gracefully(db_session):
    """Query Expansion 실패 시 빈 키워드 리스트를 반환해야 한다."""
    rag = RAGService(db_session)

    with patch("openai.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API 오류"))
        mock_openai_cls.return_value = mock_client

        keywords = await rag.expand_query("테스트 입력")

    assert keywords == []


def test_build_context_formats_correctly(db_session, sample_article):
    """build_context가 올바른 형식으로 컨텍스트를 구성해야 한다."""
    rag = RAGService(db_session)
    articles = [{
        "article_no": "제22조",
        "title": "고위험 AI 시스템",
        "content": "고위험 AI 시스템은 다음 요건을 갖춰야 한다.",
        "paragraphs": [{"paragraph_no": "①", "content": "생체정보 처리 시 동의 필요"}],
    }]
    context = rag.build_context(articles)
    assert "제22조" in context
    assert "고위험 AI 시스템" in context
    assert "①" in context


def test_build_system_prompt_includes_disclaimer(db_session):
    """시스템 프롬프트에 면책 조항이 포함되어야 한다."""
    rag = RAGService(db_session)
    prompt = rag.build_system_prompt("테스트 컨텍스트")
    assert "면책 조항" in prompt or "법적 효력이 없습니다" in prompt
