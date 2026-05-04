import httpx

from ..config import settings


class TelegramNotConfigured(Exception):
    pass


def _require_telegram_config() -> tuple[str, str]:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramNotConfigured("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    return settings.telegram_bot_token, settings.telegram_chat_id


async def send_telegram_message(text: str) -> dict:
    token, chat_id = _require_telegram_config()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
