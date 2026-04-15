import re
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.law import Article, Paragraph, Subparagraph, Item
from app.schemas.law import ArticleSchema
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

ARTICLE_PATTERN = re.compile(r'(?=제\d+조\s*\([^)]+\))')


class LawParserService:
    def __init__(self, openai_service: OpenAIService | None = None):
        self.openai_service = openai_service or OpenAIService()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """pdfplumber로 PDF 텍스트 추출."""
        import pdfplumber
        logger.info("[1/4] PDF 텍스트 추출 시작: %s", pdf_path)
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        result = "\n".join(pages)
        logger.info("[1/4] PDF 텍스트 추출 완료: %d 페이지, %d 자", len(pages), len(result))
        return result

    def split_into_chunks(self, text: str) -> list[str]:
        """조(Article) 단위로 텍스트 분할."""
        parts = ARTICLE_PATTERN.split(text)
        chunks = [p.strip() for p in parts if p.strip() and re.match(r'제\d+조', p.strip())]
        logger.info("[2/4] 청크 분할 완료: %d개 조항", len(chunks))
        return chunks

    async def parse_chunk_with_gpt(self, chunk: str) -> dict:
        """GPT로 청크를 구조화된 JSON으로 파싱."""
        result = await self.openai_service.parse_law_structure(chunk)
        # GPT가 {"articles": [...]} 형태로 감싸서 반환하는 경우 처리
        if "articles" in result and isinstance(result["articles"], list):
            articles = result["articles"]
            if articles:
                return articles[0]  # 첫 번째 조항 반환
        return result

    def validate_and_save(self, db: Session, articles_data: list[dict]) -> dict:
        """Pydantic 검증 후 트랜잭션으로 DB 저장."""
        logger.info("[3/4] Pydantic 검증 시작: %d개 파싱 결과", len(articles_data))
        validated = []
        for data in articles_data:
            try:
                validated.append(ArticleSchema(**data))
            except Exception as e:
                logger.warning("유효하지 않은 조항 데이터 스킵: %s", e)
        logger.info("[3/4] 검증 완료: %d개 유효 / %d개 스킵",
                    len(validated), len(articles_data) - len(validated))

        now = datetime.now(timezone.utc).isoformat()
        stats = {"articles": 0, "paragraphs": 0, "subparagraphs": 0, "items": 0}

        try:
            logger.info("[4/4] DB 저장 시작 (기존 데이터 삭제 후 INSERT)")
            db.query(Item).delete()
            db.query(Subparagraph).delete()
            db.query(Paragraph).delete()
            db.query(Article).delete()

            for art in validated:
                db_article = Article(
                    article_no=art.article_no,
                    title=art.title,
                    content=art.content,
                    category=art.category,
                    effective_date=art.effective_date,
                    created_at=now,
                )
                db.add(db_article)
                db.flush()
                stats["articles"] += 1

                for para in art.paragraphs:
                    db_para = Paragraph(
                        article_id=db_article.id,
                        paragraph_no=para.paragraph_no,
                        content=para.content,
                        created_at=now,
                    )
                    db.add(db_para)
                    db.flush()
                    stats["paragraphs"] += 1

                    for sub in para.subparagraphs:
                        db_sub = Subparagraph(
                            paragraph_id=db_para.id,
                            subparagraph_no=sub.subparagraph_no,
                            content=sub.content,
                            created_at=now,
                        )
                        db.add(db_sub)
                        db.flush()
                        stats["subparagraphs"] += 1

                        for item in sub.items:
                            db_item = Item(
                                subparagraph_id=db_sub.id,
                                item_no=item.item_no,
                                content=item.content,
                                created_at=now,
                            )
                            db.add(db_item)
                            stats["items"] += 1

            db.commit()
            stats["total"] = sum(stats.values())
            logger.info("[4/4] DB 저장 완료: 조 %d개, 항 %d개, 호 %d개, 목 %d개",
                        stats["articles"], stats["paragraphs"],
                        stats["subparagraphs"], stats["items"])
            return stats

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"파싱 실패: {e}") from e
