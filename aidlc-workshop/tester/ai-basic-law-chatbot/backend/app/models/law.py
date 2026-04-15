from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from app.database import Base


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_no = Column(String(20), nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    effective_date = Column(String(20), nullable=True)
    created_at = Column(String(30), nullable=False, default=_now)

    paragraphs = relationship("Paragraph", back_populates="article",
                              cascade="all, delete-orphan")


class Paragraph(Base):
    __tablename__ = "paragraphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    paragraph_no = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    effective_date = Column(String(20), nullable=True)
    created_at = Column(String(30), nullable=False, default=_now)

    article = relationship("Article", back_populates="paragraphs")
    subparagraphs = relationship("Subparagraph", back_populates="paragraph",
                                 cascade="all, delete-orphan")


class Subparagraph(Base):
    __tablename__ = "subparagraphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paragraph_id = Column(Integer, ForeignKey("paragraphs.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    subparagraph_no = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    effective_date = Column(String(20), nullable=True)
    created_at = Column(String(30), nullable=False, default=_now)

    paragraph = relationship("Paragraph", back_populates="subparagraphs")
    items = relationship("Item", back_populates="subparagraph",
                         cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subparagraph_id = Column(Integer, ForeignKey("subparagraphs.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    item_no = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    effective_date = Column(String(20), nullable=True)
    created_at = Column(String(30), nullable=False, default=_now)

    subparagraph = relationship("Subparagraph", back_populates="items")


class Embedding(Base):
    __tablename__ = "embeddings"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"),
                        nullable=False, unique=True, index=True)
    vector     = Column(LargeBinary, nullable=False)
    model      = Column(String(50), nullable=False, default="text-embedding-3-small")
    created_at = Column(String(30), nullable=False, default=_now)

    article = relationship("Article", backref="embedding")


class GuidelineChunk(Base):
    __tablename__ = "guideline_chunks"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    source           = Column(String(200), nullable=False)
    page_no          = Column(Integer, nullable=True)
    content          = Column(Text, nullable=False)
    vector           = Column(LargeBinary, nullable=False)
    model            = Column(String(50), nullable=False, default="text-embedding-3-small")
    related_articles = Column(Text, nullable=True)   # JSON 배열: ["제3조", "제22조"]
    created_at       = Column(String(30), nullable=False, default=_now)
