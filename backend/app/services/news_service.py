import re
from .stock_service import get_news as _get_raw_news

# Strong bullish signals — standalone words unlikely to be flipped by context
BULLISH_STRONG = {
    "surge", "surges", "surging", "rally", "rallies", "soar", "soars", "soared",
    "beat", "beats", "blowout", "breakout", "upgrade", "upgraded", "outperform",
    "buyback", "approval", "approved", "record high", "all-time high",
    "above estimates", "strong quarter", "bullish",
}

# Moderate bullish — common in positive headlines
BULLISH_MOD = {
    "gains", "gain", "higher", "jumps", "jumped", "rises", "rose",
    "profit", "profits", "growth", "partnership", "deal", "breakthrough",
    "raises price target", "positive", "strong",
}

# Strong bearish signals
BEARISH_STRONG = {
    "crash", "collapse", "bankruptcy", "default", "recall", "fraud",
    "investigation", "lawsuit", "layoffs", "downgrade", "downgraded",
    "below estimates", "miss", "misses", "missed", "bearish",
}

# Moderate bearish
BEARISH_MOD = {
    "drops", "dropped", "falls", "fell", "decline", "declines", "declined",
    "loss", "losses", "warning", "concern", "concerns", "probe",
    "underperform", "disappoints", "disappointed", "weak",
}

# Words that flip meaning when appearing BEFORE a bearish keyword
# e.g. "cuts LOSSES" → positive, "up after SELLING" → positive context
NEGATION_PATTERNS = [
    r"\bup\b.{0,40}(sell|selling|cut|drop|loss)",  # "up after selling"
    r"\brises?\b.{0,40}(sell|cut|drop|loss)",
    r"cut(s|ting)?\s+(its\s+)?(losses|debt)",       # "cuts losses/debt" → positive
    r"sell(s|ing)?\s+.{0,20}\s+to\s+(pivot|expand|grow|fund)",  # "sells X to pivot"
]


def _is_negated(lower: str, keyword: str) -> bool:
    """Check if a bearish keyword is in a negating/positive context."""
    for pat in NEGATION_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def _score_title(title: str) -> str:
    lower = title.lower()

    bull = sum(2 for w in BULLISH_STRONG if w in lower)
    bull += sum(1 for w in BULLISH_MOD if w in lower)

    bear = 0
    for w in BEARISH_STRONG:
        if w in lower and not _is_negated(lower, w):
            bear += 2
    for w in BEARISH_MOD:
        if w in lower and not _is_negated(lower, w):
            bear += 1

    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def get_news_with_sentiment(symbol: str) -> tuple[list[dict], str, float]:
    """Returns (news_items, overall_sentiment, news_score 0-100)."""
    raw = _get_raw_news(symbol)
    items = []
    bull_count = 0
    bear_count = 0

    for n in raw:
        sentiment = _score_title(n.get("title", ""))
        items.append({**n, "sentiment": sentiment})
        if sentiment == "bullish":
            bull_count += 1
        elif sentiment == "bearish":
            bear_count += 1

    total = len(items) or 1
    raw_score = 50 + ((bull_count - bear_count) / total) * 50
    news_score = max(0.0, min(100.0, raw_score))

    if bull_count > bear_count:
        overall = "bullish"
    elif bear_count > bull_count:
        overall = "bearish"
    else:
        overall = "neutral"

    return items, overall, news_score
