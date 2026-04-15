import logging
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.law import Article, Paragraph, Embedding
from app.services.embedding_service import EmbeddingService
from app.config import settings
from typing import List

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self._embedding_service: EmbeddingService | None = None

    def _get_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _has_embeddings(self) -> bool:
        return self.db.query(Embedding).first() is not None

    async def expand_query(self, query: str) -> list[str]:
        """GPT-4o mini로 법적 쟁점 키워드 추출 (Query Expansion)."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = (
            "다음 AI 프로젝트 설명에서 한국 AI 기본법과 관련된 핵심 법적 쟁점 키워드를 "
            "5개 이내로 추출하세요. 쉼표로 구분하여 키워드만 반환하세요.\n"
            f"설명: {query}"
        )
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
            )
            raw = response.choices[0].message.content or ""
            keywords = [k.strip() for k in raw.split(",") if k.strip()]
            return keywords[:5]
        except Exception as e:
            logger.warning("Query Expansion 실패: %s", e)
            return []

    async def search_relevant_articles(
        self, query: str, top_k: int = 5
    ) -> tuple[List[dict], List[dict]]:
        """Query Expansion → 임베딩 검색 → (법령 조항, 가이드라인 청크) 반환."""
        if self._has_embeddings():
            return await self._search_by_embedding(query, top_k)
        else:
            logger.info("임베딩 없음 - LIKE 검색으로 폴백")
            return self._search_by_keyword(query, top_k), []

    async def _search_by_embedding(
        self, query: str, top_k: int
    ) -> List[dict]:
        """Query Expansion + 임베딩 코사인 유사도 검색 (법령 + 가이드라인)."""
        keywords = await self.expand_query(query)
        search_text = query + " " + " ".join(keywords)

        emb_service = self._get_embedding_service()
        try:
            query_vector = await emb_service.create_embedding(search_text)
            articles = emb_service.search_by_vector(self.db, query_vector, top_k=3)
            article_nos = [a["article_no"] for a in articles]
            guidelines = self._search_guidelines_by_articles(article_nos, query_vector, top_k=2)
            return articles, guidelines
        except Exception as e:
            logger.warning("임베딩 검색 실패, LIKE 폴백: %s", e)
            return self._search_by_keyword(query, top_k), []

    def _search_guidelines(self, query_vector, top_k: int = 2) -> List[dict]:
        """가이드라인 청크 검색 - 태그 기반 우선, 없으면 임베딩 유사도 폴백."""
        try:
            from app.services.guideline_service import GuidelineService
            svc = GuidelineService()
            return svc.search_guideline_chunks(self.db, query_vector, top_k)
        except Exception as e:
            logger.warning("가이드라인 검색 실패: %s", e)
            return []

    def _search_guidelines_by_articles(
        self, article_nos: List[str], query_vector, top_k: int = 2
    ) -> List[dict]:
        """검색된 법령 조항 번호로 태그된 가이드라인 청크 우선 검색."""
        import json as _json
        from app.models.law import GuidelineChunk
        import numpy as np

        # 태그 기반 검색
        tagged = []
        for chunk in self.db.query(GuidelineChunk).all():
            if not chunk.related_articles:
                continue
            try:
                articles = _json.loads(chunk.related_articles)
                if any(a in articles for a in article_nos):
                    tagged.append(chunk)
            except Exception:
                continue

        if tagged:
            # 태그된 청크 중 임베딩 유사도 상위 top_k
            q = query_vector / (np.linalg.norm(query_vector) + 1e-10)
            scores = []
            for chunk in tagged:
                v = np.frombuffer(chunk.vector, dtype=np.float32)
                v = v / (np.linalg.norm(v) + 1e-10)
                scores.append((float(np.dot(q, v)), chunk))
            scores.sort(reverse=True, key=lambda x: x[0])
            return [
                {"source": c.source, "page_no": c.page_no, "content": c.content}
                for _, c in scores[:top_k]
            ]

        # 태그 없으면 임베딩 유사도 폴백
        try:
            from app.services.guideline_service import GuidelineService
            return GuidelineService().search_guideline_chunks(self.db, query_vector, top_k)
        except Exception as e:
            logger.warning("가이드라인 폴백 검색 실패: %s", e)
            return []

    def _search_by_keyword(self, query: str, top_k: int) -> List[dict]:
        """LIKE 기반 키워드 검색 (폴백)."""
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 1][:5]
        if not keywords:
            articles = self.db.query(Article).limit(top_k).all()
        else:
            conditions = []
            for kw in keywords:
                conditions.append(Article.title.like(f"%{kw}%"))
                conditions.append(Article.content.like(f"%{kw}%"))
            articles = (
                self.db.query(Article)
                .filter(or_(*conditions))
                .limit(top_k)
                .all()
            )
            if not articles:
                articles = self.db.query(Article).limit(top_k).all()

        return self._build_article_dicts(articles)

    def _build_article_dicts(self, articles) -> List[dict]:
        """Article 목록을 조→항→호 구조의 dict 리스트로 변환."""
        from app.models.law import Subparagraph
        result = []
        for article in articles:
            paragraphs = self.db.query(Paragraph).filter(
                Paragraph.article_id == article.id
            ).all()
            para_list = []
            for p in paragraphs:
                subs = self.db.query(Subparagraph).filter(
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

    def build_context(self, articles: List[dict], guidelines: List[dict] = None) -> str:
        """검색된 조항 + 가이드라인 청크를 프롬프트용 컨텍스트로 변환."""
        lines = []

        if articles:
            lines.append("[관련 AI 기본법 조항]")
            for a in articles:
                header = f"{a['article_no']}({a['title']})"
                if a.get("content"):
                    lines.append(f"{header}: {a['content']}")
                else:
                    lines.append(header)
                for p in a.get("paragraphs", []):
                    lines.append(f"  {p['paragraph_no']} {p['content']}")
                    for s in p.get("subparagraphs", []):
                        lines.append(f"    {s['subparagraph_no']} {s['content']}")

        if guidelines:
            lines.append("\n[관련 가이드라인]")
            for g in guidelines:
                lines.append(f"[출처: {g['source']} p.{g['page_no']}]")
                lines.append(g["content"])

        return "\n".join(lines)

    def build_system_prompt(self, context: str) -> str:
        """시스템 프롬프트 구성."""
        law_section = f"{context}\n\n" if context else ""
        return (
            "당신은 한국 AI 기본법 준수 여부를 분석하는 전문 어시스턴트입니다.\n\n"
            "## 역할 범위\n"
            "오직 AI 프로젝트·서비스의 한국 AI 기본법 준수 여부 분석만 답변합니다.\n"
            "다음과 같은 경우에만 거절하세요:\n"
            "- AI 기술이나 서비스와 전혀 무관한 질문 (날씨, 요리, 스포츠 등 명백히 무관한 경우)\n"
            "이전 대화 맥락이 있거나, AI 서비스·시스템과 관련된 질문이라면 모두 분석 대상입니다.\n"
            "후속 질문, 구체적인 시나리오 질문, 법적 판단 요청도 모두 답변하세요.\n"
            "거절 시 다음과 같이 답변하세요:\n"
            "\"죄송합니다. 저는 AI 기본법 준수 여부 분석만 도와드릴 수 있습니다. "
            "AI 프로젝트나 서비스의 법적 준수 여부가 궁금하시면 해당 내용을 입력해 주세요.\"\n\n"
            "## 참고 자료\n"
            f"{law_section}"
            "## 출력 형식\n"
            "아래 세 섹션을 참고하여 자연스럽게 답변하세요. 상황에 따라 유연하게 구성해도 됩니다.\n\n"
            "### 📋 관련 법령\n"
            "- 관련 AI 기본법 조항 번호와 내용을 명시하세요.\n"
            "- 각 조항에 대해 준수(✅) / 부분 준수(⚠️) / 미준수(❌) 여부를 표시하세요.\n\n"
            "### 📌 관련 가이드라인\n"
            "- 해당 조항과 연관된 정부 가이드라인의 핵심 내용을 요약하세요.\n"
            "- 관련 가이드라인이 없으면 이 섹션은 생략해도 됩니다.\n\n"
            "### ✅ 권장 액션\n"
            "- 미준수 또는 부분 준수 항목에 대해 구체적이고 실행 가능한 개선 조치를 제시하세요.\n"
            "- 우선순위(높음/중간/낮음)를 함께 표시하세요.\n"
            "- 모든 항목이 준수인 경우 간략히 요약하세요.\n\n"
            "## 마무리\n"
            "답변 마지막에 반드시 다음 면책 조항을 포함하세요:\n"
            "> 본 결과는 참고용이며, 법적 효력이 없습니다. 정확한 법률 해석은 전문가에게 문의하세요."
        )
