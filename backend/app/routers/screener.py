from fastapi import APIRouter, HTTPException, Query
from ..services.screener_service import get_screener_results

router = APIRouter()


@router.get("/today")
def screener_today(market: str = Query("us", pattern="^(us|th|cn|gold)$")):
    try:
        return get_screener_results(market=market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
