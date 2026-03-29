from sqlalchemy.orm import Session
from app.models.models import AISettings, BotSettings
from typing import Optional, Dict, Any
import httpx
import json


class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._get_ai_settings()

    def _get_ai_settings(self) -> AISettings:
        settings = self.db.query(AISettings).first()
        if not settings:
            settings = AISettings(
                provider="ollama",
                model="llama2",
                ollama_url="http://localhost:11434",
                lmstudio_url="http://localhost:1234/v1",
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    async def analyze_market(
        self, market_question: str, market_data: Dict[str, Any]
    ) -> str:
        prompt = self._build_prompt(market_question, market_data)

        if self.settings.provider == "ollama":
            return await self._query_ollama(prompt)
        elif self.settings.provider == "lmstudio":
            return await self._query_lmstudio(prompt)
        elif self.settings.provider == "gemini":
            return await self._query_gemini(prompt)
        elif self.settings.provider == "openrouter":
            return await self._query_openrouter(prompt)
        else:
            return "HOLD"

    def _build_prompt(self, question: str, data: Dict[str, Any]) -> str:
        base_prompt = self.settings.prompt_template
        market_info = f"""
Market Question: {question}
Current YES Price: {data.get("yes_price", "N/A")}
Current NO Price: {data.get("no_price", "N/A")}
Volume: {data.get("volume", "N/A")}
"""
        return f"{base_prompt}\n{market_info}\n\nWhat should I do? (YES/NO/HOLD)"

    async def _query_ollama(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.settings.ollama_url}/api/generate",
                    json={
                        "model": self.settings.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                if response.status_code == 200:
                    return self._parse_response(response.json().get("response", ""))
        except Exception as e:
            return f"ERROR: {str(e)}"
        return "HOLD"

    async def _query_lmstudio(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.settings.lmstudio_url}/chat/completions",
                    json={
                        "model": self.settings.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    },
                )
                if response.status_code == 200:
                    return self._parse_response(
                        response.json()["choices"][0]["message"]["content"]
                    )
        except Exception as e:
            return f"ERROR: {str(e)}"
        return "HOLD"

    async def _query_gemini(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            return "ERROR: No Gemini API key configured"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={self.settings.gemini_api_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
                if response.status_code == 200:
                    return self._parse_response(
                        response.json()["candidates"][0]["content"]["parts"][0]["text"]
                    )
        except Exception as e:
            return f"ERROR: {str(e)}"
        return "HOLD"

    async def _query_openrouter(self, prompt: str) -> str:
        if not self.settings.openrouter_api_key:
            return "ERROR: No OpenRouter API key configured"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.openrouter_api_key}"
                    },
                    json={
                        "model": self.settings.model or "openai/gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                if response.status_code == 200:
                    return self._parse_response(
                        response.json()["choices"][0]["message"]["content"]
                    )
        except Exception as e:
            return f"ERROR: {str(e)}"
        return "HOLD"

    def _parse_response(self, response: str) -> str:
        response = response.upper().strip()
        if "YES" in response and "NO" not in response:
            return "YES"
        elif "NO" in response:
            return "NO"
        elif "HOLD" in response or "SKIP" in response:
            return "HOLD"
        return "HOLD"


class BotService:
    def __init__(self, db: Session):
        self.db = db

    def get_setting(self, key: str, default: Any = None) -> Any:
        setting = self.db.query(BotSettings).filter(BotSettings.key == key).first()
        if setting:
            try:
                return json.loads(setting.value)
            except:
                return setting.value
        return default

    def set_setting(self, key: str, value: Any):
        setting = self.db.query(BotSettings).filter(BotSettings.key == key).first()
        if setting:
            setting.value = (
                json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            )
        else:
            setting = BotSettings(
                key=key,
                value=json.dumps(value)
                if isinstance(value, (dict, list))
                else str(value),
            )
            self.db.add(setting)
        self.db.commit()

    def get_bot_status(self) -> Dict[str, Any]:
        return {
            "running": self.get_setting("bot_running", False),
            "auto_trade": self.get_setting("auto_trade", False),
            "stake_amount": self.get_setting("stake_amount", 10.0),
            "selected_markets": self.get_setting("selected_markets", []),
        }

    def set_bot_status(
        self, running: bool = None, auto_trade: bool = None, stake_amount: float = None
    ):
        if running is not None:
            self.set_setting("bot_running", running)
        if auto_trade is not None:
            self.set_setting("auto_trade", auto_trade)
        if stake_amount is not None:
            self.set_setting("stake_amount", stake_amount)
