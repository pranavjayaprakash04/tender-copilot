from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.dependencies import (
    get_current_user_id,
    get_db_session,
    get_trace_id,
)

router = APIRouter(prefix="/bids", tags=["bid-lifecycle"])

# ── Shared SELECT columns (maps tenders → bid-shaped response) ────────────────
TENDER_AS_BID = """
    id::text            AS id,
    tender_id,
    title               AS tender_title,
    organization,
    portal              AS source,
    COALESCE(url, detail_url) AS source_url,
    apply_url,
    category,
    status,
    location            AS state,
    bid_end_date::text  AS deadline,
    estimated_value::text AS estimated_value,
    emd_amount::text    AS emd_amount,
    scraped_at::text    AS posted_date,
    required_documents,
    details
"""


def _days_label(bid_end_date_str) -> str:
    return bid_end_date_str or ""


# ── GET /bids  ────────────────────────────────────────────────────────────────
@router.get("")
async def list_bids(
    search: str | None = Query(None),
    status: str | None = Query(None),          # active | closing_soon | closed | all
    category: str | None = Query(None),
    state: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """
    Return tenders as a bid pipeline view.
    status=active        → tenders where bid_end_date >= today
    status=closing_soon  → tenders closing within 7 days
    status=closed        → tenders where bid_end_date < today
    status omitted/all   → everything
    """
    conditions = ["1=1"]
    params: dict = {}

    if search:
        conditions.append(
            "(title ILIKE :search OR organization ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    if category:
        conditions.append("category ILIKE :category")
        params["category"] = f"%{category}%"

    if state:
        conditions.append("location ILIKE :state")
        params["state"] = f"%{state}%"

    # Map frontend status filter → SQL date condition
    if status == "active":
        conditions.append("bid_end_date >= CURRENT_DATE")
    elif status == "closing_soon":
        conditions.append(
            "bid_end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'"
        )
    elif status == "closed":
        conditions.append("bid_end_date < CURRENT_DATE")
    # else: all — no extra condition

    where = " AND ".join(conditions)
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    total = (
        await session.execute(
            text(f"SELECT COUNT(*) FROM tenders WHERE {where}"), params
        )
    ).scalar()

    rows = await session.execute(
        text(f"""
            SELECT {TENDER_AS_BID}
            FROM tenders
            WHERE {where}
            ORDER BY bid_end_date ASC NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    bids = [dict(r._mapping) for r in rows]

    return {
        "bids": bids,
        "total": total,
        "page": page,
        "limit": limit,
    }


# ── GET /bids/stats/overview  ─────────────────────────────────────────────────
@router.get("/stats/overview")
async def get_bid_stats(
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    row = (
        await session.execute(
            text("""
                SELECT
                    COUNT(*)                                                        AS total,
                    COUNT(*) FILTER (WHERE bid_end_date >= CURRENT_DATE)            AS active,
                    COUNT(*) FILTER (WHERE bid_end_date < CURRENT_DATE)             AS closed,
                    COUNT(*) FILTER (
                        WHERE bid_end_date BETWEEN CURRENT_DATE
                          AND CURRENT_DATE + INTERVAL '7 days'
                    )                                                               AS closing_soon,
                    COUNT(DISTINCT portal)                                          AS portals,
                    COUNT(DISTINCT category)                                        AS categories
                FROM tenders
            """)
        )
    ).mappings().one()

    return {"data": dict(row)}


# ── GET /bids/{bid_id}  ───────────────────────────────────────────────────────
@router.get("/{bid_id}")
async def get_bid(
    bid_id: str,
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """Fetch a single tender by UUID or scraper tender_id."""
    row = (
        await session.execute(
            text(f"""
                SELECT {TENDER_AS_BID}
                FROM tenders
                WHERE id::text = :tid
                   OR tender_id = :tid
                LIMIT 1
            """),
            {"tid": bid_id},
        )
    ).mappings().first()

    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tender not found")

    return {"data": dict(row)}
