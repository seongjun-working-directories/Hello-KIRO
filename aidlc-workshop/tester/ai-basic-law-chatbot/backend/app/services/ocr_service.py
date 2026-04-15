"""
스캔본 PDF OCR 서비스.
pymupdf로 페이지를 이미지로 변환 후 GPT-4o Vision으로 텍스트 추출.
"""
import base64
import logging
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.law import GuidelineChunk
from app.services.embedding_service import EmbeddingService
from app.config import settings

logger = logging.getLogger(__name__)

MIN_TEXT_LEN = 50  # OCR 결과가 너무 짧으면 스킵


class OCRService:
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_service = EmbeddingService()

    def _pdf_page_to_base64(self, pdf_path: str, page_no: int) -> str:
        """pymupdf로 PDF 페이지를 PNG 이미지로 변환 후 base64 인코딩."""
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        page = doc[page_no - 1]
        # 해상도 2x (144 DPI) - OCR 품질 향상
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()
        return base64.b64encode(img_bytes).decode("utf-8")

    async def extract_text_from_page(self, pdf_path: str, page_no: int) -> str:
        """GPT-4o Vision으로 페이지 텍스트 추출."""
        img_b64 = self._pdf_page_to_base64(pdf_path, page_no)
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "이 이미지는 한국 AI 가이드라인 문서의 한 페이지입니다. "
                                "페이지의 모든 텍스트를 정확하게 추출해주세요. "
                                "표, 목록, 제목 등 모든 내용을 포함하고 "
                                "이미지나 도표 설명은 제외하세요. "
                                "텍스트만 반환하세요."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""

    async def embed_scanned_pdf(self, db: Session, pdf_path: str) -> dict:
        """스캔본 PDF를 OCR로 텍스트 추출 후 임베딩 저장."""
        import fitz
        source = Path(pdf_path).name
        logger.info("[OCR] %s 처리 시작", source)

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        logger.info("[OCR] 총 %d 페이지", total_pages)

        # 기존 청크 삭제
        deleted = db.query(GuidelineChunk).filter(
            GuidelineChunk.source == source
        ).delete()
        if deleted:
            logger.info("[OCR] 기존 청크 %d개 삭제", deleted)

        now = datetime.now(timezone.utc).isoformat()
        success, failed, skipped = 0, 0, 0

        for page_no in range(1, total_pages + 1):
            try:
                logger.info("[OCR] %d/%d 페이지 텍스트 추출 중...", page_no, total_pages)
                text = await self.extract_text_from_page(pdf_path, page_no)

                if not text or len(text.strip()) < MIN_TEXT_LEN:
                    logger.info("[OCR] %d/%d 페이지 스킵 (텍스트 부족)", page_no, total_pages)
                    skipped += 1
                    continue

                vector = await self.embedding_service.create_embedding(text)
                db.add(GuidelineChunk(
                    source=source,
                    page_no=page_no,
                    content=text.strip(),
                    vector=vector.tobytes(),
                    model="text-embedding-3-small",
                    created_at=now,
                ))
                db.flush()
                success += 1

            except Exception as e:
                logger.warning("[OCR] %d/%d 페이지 실패: %s", page_no, total_pages, e)
                failed += 1

        db.commit()
        logger.info("[OCR] %s 완료 - 성공 %d개, 실패 %d개, 스킵 %d개",
                    source, success, failed, skipped)
        return {"source": source, "success": success, "failed": failed, "skipped": skipped}
