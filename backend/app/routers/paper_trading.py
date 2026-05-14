from fastapi import APIRouter, HTTPException, Query

from ..services.paper_trading_service import get_paper_trading_summary

router = APIRouter()


@router.get("/summary")
def paper_trading_summary(market: str = Query("us", pattern="^(us|th|cn|gold|crypto)$")):
    try:
        return get_paper_trading_summary(market=market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
