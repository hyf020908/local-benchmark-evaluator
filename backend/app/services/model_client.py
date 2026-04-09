from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


class ModelClientError(RuntimeError):
    pass


@dataclass
class OpenAICompatibleClient:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 120

    def _build_endpoint(self) -> str:
        raw = self.base_url.rstrip("/")
        if raw.endswith("/chat/completions"):
            return raw
        if raw.endswith("/v1"):
            return f"{raw}/chat/completions"
        return f"{raw}/v1/chat/completions"

    async def complete(self, prompt: str, temperature: float = 0.0) -> str:
        endpoint = self._build_endpoint()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ModelClientError(f"模型请求超时：{exc}") from exc
        except httpx.RequestError as exc:
            raise ModelClientError(f"连接模型服务失败：{exc}") from exc

        if response.status_code == 401:
            raise ModelClientError("模型服务认证失败，请检查 api_key。")
        if response.status_code == 404:
            raise ModelClientError("模型服务地址或模型名称不存在。")
        if response.status_code >= 400:
            body = response.text[:400]
            raise ModelClientError(
                f"模型服务返回错误状态码 {response.status_code}: {body}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ModelClientError(
                f"模型服务返回了非 JSON 响应：{response.text[:400]}"
            ) from exc

        choices = data.get("choices")
        if not choices:
            raise ModelClientError("模型服务返回为空，未包含 choices 字段。")

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            content = "\n".join(text_parts).strip()

        if not isinstance(content, str) or not content.strip():
            raise ModelClientError("模型返回内容为空。")
        return content.strip()
