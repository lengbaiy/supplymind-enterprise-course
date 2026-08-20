import json

import httpx
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import get_settings


class ModelConfigurationError(RuntimeError):
    pass


class ModelResponseError(RuntimeError):
    pass


class AnswerPlan(BaseModel):
    direct_answer: str = Field(min_length=1)
    facts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class OpenAICompatibleClient:
    @staticmethod
    def _openai_messages(messages) -> list[dict[str, str]]:
        """Translate LangChain message types to OpenAI-compatible roles."""
        roles = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}
        return [
            {"role": roles.get(message.type, message.type), "content": message.content}
            for message in messages
        ]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if (
            not settings.embedding_base_url
            or not settings.embedding_model
            or not settings.embedding_api_key
        ):
            raise ModelConfigurationError(
                "Embedding model configuration is required for knowledge retrieval"
            )
        url = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
                json={"model": settings.embedding_model, "input": texts},
            )
        if response.status_code >= 400:
            raise ModelResponseError("Embedding model request failed")
        try:
            rows = response.json()["data"]
            vectors = [row["embedding"] for row in sorted(rows, key=lambda row: row["index"])]
            if len(vectors) != len(texts) or not all(
                isinstance(vector, list) for vector in vectors
            ):
                raise TypeError("Embedding response fields are invalid")
            return vectors
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelResponseError("Embedding model returned an invalid response") from exc

    async def plan_sql(
        self,
        question: str,
        schema: list[str] | list[dict],
        context: list[str] | None = None,
    ) -> dict:
        settings = get_settings()
        if not settings.chat_base_url or not settings.chat_model or not settings.chat_api_key:
            raise ModelConfigurationError(
                "Chat model configuration is required before analysis can run"
            )
        schema_text = "; ".join(
            f"{item.get('name')}: "
            + ", ".join(column.get("name", "") for column in item.get("columns", []))
            if isinstance(item, dict)
            else str(item)
            for item in schema
        )
        context_text = "\n".join(context[-8:]) if context else "（无历史上下文）"
        prompt_template = ChatPromptTemplate.from_messages(
            [("system", "Return valid JSON only."), ("user", "{prompt}")]
        )
        prompt = (
            "You are a read-only manufacturing analytics SQL planner. Return only JSON with keys sql and insight. "
            "Use only the allowed tables. SQL must be a single SELECT or WITH statement. "
            "Use the current question as the source of truth. Use history only to resolve references such as '它' or '继续看', "
            "and never repeat an old question as a new task. "
            f"Allowed tables and columns: {schema_text}. Never invent column names. "
            f"Recent conversation:\n{context_text}\nCurrent user question: {question}"
        )
        formatted_prompt = prompt_template.format_messages(prompt=prompt)
        url = f"{settings.chat_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.chat_api_key}"},
                json={
                    "model": settings.chat_model,
                    "temperature": 0,
                    "messages": self._openai_messages(formatted_prompt),
                },
            )
        if response.status_code >= 400:
            raise ModelResponseError("Chat model request failed")
        try:
            content = response.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            if not isinstance(result.get("sql"), str) or not isinstance(result.get("insight"), str):
                raise TypeError("Model plan fields are invalid")
            return {"sql": result["sql"], "insight": result["insight"]}
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelResponseError("Chat model returned an invalid analysis plan") from exc

    async def answer_question(
        self,
        question: str,
        rows: list[dict],
        citations: list[dict],
        context: list[str] | None = None,
        planner_insight: str = "",
    ) -> AnswerPlan:
        """Generate an evidence-bound answer using LangChain structured output."""
        settings = get_settings()
        if not settings.chat_base_url or not settings.chat_model or not settings.chat_api_key:
            raise ModelConfigurationError(
                "Chat model configuration is required before analysis can run"
            )
        parser = PydanticOutputParser(pydantic_object=AnswerPlan)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an enterprise supply-chain analyst. Answer only from the supplied query rows and citations. {format_instructions}",
                ),
                (
                    "user",
                    "Question: {question}\nPlanner note: {planner_insight}\nRows: {rows}\nCitations: {citations}\nContext: {context}",
                ),
            ]
        )
        messages = prompt.format_messages(
            format_instructions=parser.get_format_instructions(),
            question=question,
            planner_insight=planner_insight,
            rows=json.dumps(rows[:100], ensure_ascii=False, default=str),
            citations=json.dumps(citations[:10], ensure_ascii=False, default=str),
            context="\n".join((context or [])[-8:]) or "（无历史上下文）",
        )
        url = f"{settings.chat_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.chat_api_key}"},
                json={
                    "model": settings.ai_answer_model or settings.chat_model,
                    "temperature": 0,
                    "messages": self._openai_messages(messages),
                },
            )
        if response.status_code >= 400:
            raise ModelResponseError("Chat model answer request failed")
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return parser.parse(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelResponseError("Chat model returned an invalid structured answer") from exc
