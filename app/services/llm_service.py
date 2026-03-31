import httpx

from app.core.config import settings


class LLMService:
    """
    Upstage Solar API를 사용해 최종 답변 생성.
    OpenAI 호환 형식이라 messages 구조를 그대로 사용한다.
    """

    def __init__(self):
        self._api_url = f"{settings.upstage_base_url}/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {settings.upstage_api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """
        Args:
            system_prompt: 역할 및 지시사항
            messages: [{"role": "user"|"assistant", "content": "..."}]
            temperature: 낮을수록 일관된 답변 (사실 기반 QA에는 0.1~0.3 권장)
        Returns:
            생성된 답변 텍스트
        """
        payload = {
            "model": "solar-pro",
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._api_url,
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
