import logging
import os
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.law import GuidelineChunk
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

GUIDELINE_DIR = Path(__file__).parent.parent.parent / "data" / "guidelines"
MIN_CHUNK_LEN = 100  # 너무 짧은 청크 스킵


class GuidelineService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def extract_pages(self, pdf_path: str) -> list[dict]:
        """PDF에서 페이지별 텍스트 추출."""
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and len(text.strip()) >= MIN_CHUNK_LEN:
                    pages.append({"page_no": i, "content": text.strip()})
        return pages

    async def embed_guideline_file(self, db: Session, pdf_path: str) -> dict:
        """단일 가이드라인 PDF를 청크 단위로 임베딩하여 저장."""
        source = Path(pdf_path).name
        logger.info("[가이드라인] %s 처리 시작", source)

        # 기존 해당 파일 청크 삭제
        deleted = db.query(GuidelineChunk).filter(
            GuidelineChunk.source == source
        ).delete()
        if deleted:
            logger.info("[가이드라인] 기존 청크 %d개 삭제", deleted)

        pages = self.extract_pages(pdf_path)
        logger.info("[가이드라인] %s: %d 페이지 추출", source, len(pages))

        now = datetime.now(timezone.utc).isoformat()
        success, failed = 0, 0

        for page in pages:
            try:
                logger.info("[가이드라인] %s p.%d 임베딩 중...", source, page["page_no"])
                vector = await self.embedding_service.create_embedding(page["content"])
                db.add(GuidelineChunk(
                    source=source,
                    page_no=page["page_no"],
                    content=page["content"],
                    vector=vector.tobytes(),
                    model="text-embedding-3-small",
                    created_at=now,
                ))
                db.flush()
                success += 1
            except Exception as e:
                logger.warning("[가이드라인] %s p.%d 실패: %s",
                               source, page["page_no"], e)
                failed += 1

        db.commit()
        logger.info("[가이드라인] %s 완료 - 성공 %d개, 실패 %d개",
                    source, success, failed)
        return {"source": source, "success": success, "failed": failed}

    async def embed_all_guidelines(self, db: Session, guideline_dir: str) -> dict:
        """디렉토리 내 모든 PDF 가이드라인 임베딩."""
        pdf_files = list(Path(guideline_dir).glob("*.pdf"))
        logger.info("[가이드라인] 총 %d개 파일 처리 시작", len(pdf_files))

        total_success, total_failed = 0, 0
        results = []
        for pdf_path in pdf_files:
            result = await self.embed_guideline_file(db, str(pdf_path))
            results.append(result)
            total_success += result["success"]
            total_failed += result["failed"]

        logger.info("[가이드라인] 전체 완료 - 성공 %d개, 실패 %d개",
                    total_success, total_failed)
        return {
            "files": len(pdf_files),
            "total_chunks": total_success,
            "failed": total_failed,
            "details": results,
        }

    def search_guideline_chunks(
        self, db: Session, query_vector: np.ndarray, top_k: int = 2
    ) -> list[dict]:
        """코사인 유사도로 관련 가이드라인 청크 검색."""
        chunks = db.query(GuidelineChunk).all()
        if not chunks:
            return []

        q = query_vector / (np.linalg.norm(query_vector) + 1e-10)
        scores = []
        for chunk in chunks:
            v = np.frombuffer(chunk.vector, dtype=np.float32)
            v = v / (np.linalg.norm(v) + 1e-10)
            score = float(np.dot(q, v))
            scores.append((score, chunk))

        scores.sort(reverse=True, key=lambda x: x[0])
        return [
            {
                "source": c.source,
                "page_no": c.page_no,
                "content": c.content,
            }
            for _, c in scores[:top_k]
        ]

    async def tag_chunk(self, content: str) -> list[str]:
        """GPT-4o mini로 청크의 관련 AI 기본법 조항 번호 추출."""
        from openai import AsyncOpenAI
        from app.config import settings
        import json as _json
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = (
            "다음 AI 가이드라인 텍스트가 한국 AI 기본법의 어떤 조항과 관련되는지 "
            "조항 번호만 JSON 배열로 반환하세요. 관련 없으면 빈 배열 []을 반환하세요.\n"
            '예: ["제3조", "제22조"]\n\n'
            f"텍스트:\n{content[:1000]}"  # 토큰 절약을 위해 1000자로 제한
        )
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
            )
            raw = response.choices[0].message.content or "[]"
            # JSON 배열 추출
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return _json.loads(raw[start:end])
            return []
        except Exception as e:
            logger.warning("태깅 실패: %s", e)
            return []

    async def tag_all_chunks(self, db: Session) -> dict:
        """모든 가이드라인 청크에 관련 법령 조항 태깅."""
        import json as _json
        chunks = db.query(GuidelineChunk).all()
        total = len(chunks)
        logger.info("[태깅] 총 %d개 청크 태깅 시작", total)

        success, failed = 0, 0
        for i, chunk in enumerate(chunks, 1):
            try:
                logger.info("[태깅] %d/%d - %s p.%s", i, total, chunk.source, chunk.page_no)
                articles = await self.tag_chunk(chunk.content)
                chunk.related_articles = _json.dumps(articles, ensure_ascii=False)
                db.flush()
                success += 1
            except Exception as e:
                logger.warning("[태깅] %d/%d 실패: %s", i, total, e)
                failed += 1

        db.commit()
        logger.info("[태깅] 완료 - 성공 %d개, 실패 %d개", success, failed)
        return {"total": total, "success": success, "failed": failed}
