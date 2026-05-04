from fastapi import APIRouter, HTTPException, Query
from ..services.news_summarizer import get_summary, translate_title

router = APIRouter()


@router.get("/summarize")
def summarize_news(
    url: str = Query(..., description="Article URL"),
    title: str = Query(..., description="Article title"),
    symbol: str = Query(..., description="Stock symbol"),
    lang: str = Query("th", pattern="^(th|en)$"),
):
    try:
        summary = get_summary(url=url, title=title, symbol=symbol, lang=lang)
        return {"summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {e}")


@router.get("/translate")
def translate_news_title(
    title: str = Query(..., description="Article title to translate"),
):
    try:
        translated = translate_title(title)
        return {"title": translated}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")
