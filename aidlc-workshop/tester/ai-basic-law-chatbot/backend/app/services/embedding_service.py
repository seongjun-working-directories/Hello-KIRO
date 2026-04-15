import logging
import numpy as np
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.law import Article, Paragraph, Embedding
from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingService:
    def __init__(self, api_key: str | None = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    async def create_embedding(self, text: str) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환."""
        response = await self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def _article_to_text(self, db: Session, article: Article) -> str:
        """조항 전체 텍스트 구성 (article + 모든 하위 항목)."""
        parts = [f"{article.article_no}({article.title})"]
        if article.content:
            parts.append(article.content)
        paragraphs = db.query(Paragraph).filter(
            Paragraph.article_id == article.id
        ).all()
        for p in paragraphs:
            parts.append(f"  {p.paragraph_no} {p.content}")
        return " ".join(parts)

    async def embed_all_articles(self, db: Session) -> dict:
        """DB의 모든 조항을 임베딩하여 저장."""
        articles = db.query(Article).all()
        total = len(articles)
        logger.info("[임베딩] 총 %d개 조항 임베딩 시작", total)
        now = datetime.now(timezone.utc).isoformat()
        success, failed = 0, 0

        for i, article in enumerate(articles, 1):
            try:
                logger.info("[임베딩] %d/%d - %s(%s)", i, total, article.article_no, article.title)
                text = self._article_to_text(db, article)
                vector = await self.create_embedding(text)
                vector_bytes = vector.tobytes()

                existing = db.query(Embedding).filter(
                    Embedding.article_id == article.id
                ).first()
                if existing:
                    existing.vector = vector_bytes
                    existing.created_at = now
                else:
                    db.add(Embedding(
                        article_id=article.id,
                        vector=vector_bytes,
                        model=EMBEDDING_MODEL,
                        created_at=now,
                    ))
                db.flush()
                success += 1
            except Exception as e:
                logger.warning("[임베딩] %d/%d 실패 - %s: %s", i, total, article.article_no, e)
                failed += 1

        db.commit()
        return {"embedded": success, "failed": failed, "total": len(articles)}

    def search_by_vector(
        self, db: Session, query_vector: np.ndarray, top_k: int = 5
    ) -> list[dict]:
        """코사인 유사도 기반 상위 조항 검색."""
        embeddings = db.query(Embedding).all()
        if not embeddings:
            return []

        q = query_vector / (np.linalg.norm(query_vector) + 1e-10)
        scores = []
        for emb in embeddings:
            v = np.frombuffer(emb.vector, dtype=np.float32)
            v = v / (np.linalg.norm(v) + 1e-10)
            score = float(np.dot(q, v))
            scores.append((score, emb.article_id))

        scores.sort(reverse=True)
        top_ids = [article_id for _, article_id in scores[:top_k]]

        result = []
        for article_id in top_ids:
            article = db.query(Article).filter(Article.id == article_id).first()
            if not article:
                continue
            paragraphs = db.query(Paragraph).filter(
                Paragraph.article_id == article.id
            ).all()
            from app.models.law import Subparagraph
            para_list = []
            for p in paragraphs:
                subs = db.query(Subparagraph).filter(
                    Subparagraph.paragraph_id == p.id
                ).all()
                para_list.append({
                    "paragraph_no": p.paragraph_no,
                    "content": p.content,
                    "subparagraphs": [
                        {"subparagraph_no": s.subparagraph_no, "content": s.content}
                        for s in subs
                    ],
                })
            result.append({
                "article_no": article.article_no,
                "title": article.title,
                "content": article.content or "",
                "paragraphs": para_list,
            })
        return result
