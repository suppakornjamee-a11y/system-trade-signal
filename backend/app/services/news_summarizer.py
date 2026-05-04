import re
import httpx
from bs4 import BeautifulSoup
from .. import cache as _cache
from ..config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_MAX_TEXT = 4000


def _fetch_article_text(url: str) -> str:
    try:
        with httpx.Client(timeout=8, follow_redirects=True, headers=_HEADERS) as c:
            r = c.get(url)
            soup = BeautifulSoup(r.text, "lxml")

            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                tag.decompose()

            # Try article body first, fallback to all paragraphs
            article = soup.find("article") or soup.find("main") or soup.body
            if article:
                paragraphs = article.find_all("p")
                text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
            else:
                text = soup.get_text(separator=" ", strip=True)

            text = re.sub(r"\s+", " ", text).strip()
            return text[:_MAX_TEXT]
    except Exception:
        return ""


def _summarize_with_claude(title: str, article_text: str, symbol: str, lang: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)

    content_block = article_text if len(article_text) > 100 else f"(เฉพาะหัวข้อข่าว) {title}"

    if lang == "th":
        instruction = (
            f"สรุปข่าวหุ้น {symbol} ด้านล่างเป็นภาษาไทย 3-4 ประโยค "
            "ให้อ่านง่าย เน้น: เกิดอะไรขึ้น, ผลกระทบต่อราคา, และข้อควรระวังสำหรับนักลงทุน "
            "ตอบเฉพาะเนื้อหาสรุป ไม่ต้องมีคำนำหรือคำลงท้าย"
        )
    else:
        instruction = (
            f"Summarize this {symbol} stock news in 3-4 easy-to-read sentences. "
            "Focus on: what happened, price impact, and key takeaway for traders. "
            "Reply with the summary only, no intro or closing."
        )

    prompt = f"{instruction}\n\nTitle: {title}\n\nContent:\n{content_block}"

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def translate_title(title: str) -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    cache_key = f"title_th:{title}"
    cached = _cache.get(cache_key, ttl=86400)
    if cached:
        return cached

    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "แปลหัวข้อข่าวหุ้นต่อไปนี้เป็นภาษาไทย "
                "ตอบเฉพาะหัวข้อที่แปลแล้ว ไม่ต้องมีคำอธิบายเพิ่ม:\n\n" + title
            ),
        }],
    )

    translated = msg.content[0].text.strip()
    _cache.set(cache_key, translated)
    return translated


def get_summary(url: str, title: str, symbol: str, lang: str = "th") -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    cache_key = f"summary:{url}:{lang}"
    cached = _cache.get(cache_key, ttl=3600)
    if cached:
        return cached

    article_text = _fetch_article_text(url)
    summary = _summarize_with_claude(title, article_text, symbol, lang)

    _cache.set(cache_key, summary)
    return summary
