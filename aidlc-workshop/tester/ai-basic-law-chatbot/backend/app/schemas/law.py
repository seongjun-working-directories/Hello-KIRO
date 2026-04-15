from pydantic import BaseModel
from typing import List, Optional


class ItemSchema(BaseModel):
    item_no: str
    content: str


class SubparagraphSchema(BaseModel):
    subparagraph_no: str
    content: str
    items: List[ItemSchema] = []


class ParagraphSchema(BaseModel):
    paragraph_no: str
    content: str
    subparagraphs: List[SubparagraphSchema] = []


class ArticleSchema(BaseModel):
    article_no: str
    title: str
    content: Optional[str] = None
    category: Optional[str] = None
    effective_date: Optional[str] = None
    paragraphs: List[ParagraphSchema] = []


class ParsedLawSchema(BaseModel):
    articles: List[ArticleSchema]
    total_articles: int
    parsed_at: str


class ParseLawResponse(BaseModel):
    status: str
    message: str
    stats: dict
    processed_at: str
