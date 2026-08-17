import json

import httpx

from app.core.config import get_settings


class ModelConfigurationError(RuntimeError):
    pass


class ModelResponseError(RuntimeError):
    pass


class OpenAICompatibleClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if not settings.embedding_base_url or not settings.embedding_model or not settings.embedding_api_key:
            raise ModelConfigurationError("Embedding model configuration is required for knowledge retrieval")
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
            if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
                raise TypeError("Embedding response fields are invalid")
            return vectors
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelResponseError("Embedding model returned an invalid response") from exc

    async def plan_sql(self, question: str, schema: list[str]) -> dict:
        settings = get_settings()
        if not settings.chat_base_url or not settings.chat_model or not settings.chat_api_key:
            raise ModelConfigurationError("Chat model configuration is required before analysis can run")
        prompt = (
            "You are a read-only manufacturing analytics SQL planner. Return only JSON with keys sql and insight. "
            "Use only the allowed tables. SQL must be a single SELECT or WITH statement. "
            f"Allowed tables: {', '.join(schema)}. User question: {question}"
        )
        url = f"{settings.chat_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.chat_api_key}"},
                json={
                    "model": settings.chat_model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
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
