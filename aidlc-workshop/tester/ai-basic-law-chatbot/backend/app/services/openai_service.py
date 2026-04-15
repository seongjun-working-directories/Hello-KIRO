import asyncio
import json
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIError
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self, api_key: str | None = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            timeout=60.0,
        )
        self.model = "gpt-4o-mini"
        self.max_retries = 3

    async def _call_with_retry(self, func, *args, **kwargs):
        """Exponential backoff 재시도 (최대 3회, 1s/2s/4s)."""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError:
                raise
            except (APITimeoutError, APIError) as e:
                if attempt == self.max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning("OpenAI API error (attempt %d/%d): %s. Retrying in %ds",
                               attempt + 1, self.max_retries, e, wait)
                await asyncio.sleep(wait)

    async def stream_chat(
        self,
        system_prompt: str,
        history: list,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """GPT-4o mini 스트리밍 응답 생성."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        stream = await self._call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def parse_law_structure(self, text_chunk: str) -> dict:
        """법령 텍스트 청크를 구조화된 JSON으로 파싱 (비스트리밍)."""
        prompt = (
            "다음 법령 텍스트를 JSON 구조로 파싱하세요.\n"
            '형식: {"article_no": "제N조", "title": "...", "content": "...", '
            '"paragraphs": [{"paragraph_no": "①", "content": "...", '
            '"subparagraphs": [{"subparagraph_no": "1.", "content": "...", '
            '"items": [{"item_no": "가.", "content": "..."}]}]}]}\n\n'
            f"텍스트:\n{text_chunk}"
        )

        response = await self._call_with_retry(
            self.client.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
