from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.dependencies import (
    get_current_company_id,
    get_current_user_id,
    get_db_session,
    get_trace_id,
)

router = APIRouter(prefix="/tenders", tags=["tender-discovery"])


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_where(search, category, state, deadline):
    conditions = ["1=1"]
    params: dict = {}

    if search:
        conditions.append("(title ILIKE :search OR organization ILIKE :search)")
        params["search"] = f"%{search}%"

    if category:
        conditions.append("category ILIKE :category")
        params["category"] = f"%{category}%"

    if state:
        conditions.append("location ILIKE :state")
        params["state"] = f"%{state}%"

    if deadline:
        try:
            days = int(deadline)
            conditions.append(
                "bid_end_date <= CURRENT_DATE + :days * INTERVAL '1 day'"
            )
            params["days"] = days
        except ValueError:
            pass

    return " AND ".join(conditions), params


TENDER_SELECT = """
    id::text            AS id,
    tender_id,
    title,
    organization,
    portal              AS source,
    COALESCE(url, detail_url) AS source_url,
    apply_url,
    category,
    status,
    location            AS state,
    bid_end_date::text  AS deadline,
    estimated_value::text AS value,
    emd_amount::text    AS emd_amount,
    scraped_at::text    AS posted_date,
    required_documents,
    details
"""


# ── IMPORTANT: specific routes MUST come before /{tender_id} ─────────────────

@router.get("")
async def list_tenders(
    search: str | None = Query(None),
    category: str | None = Query(None),
    state: str | None = Query(None),
    deadline: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """List tenders from the real scraper table."""
    where, params = _build_where(search, category, state, deadline)
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
            SELECT {TENDER_SELECT}
            FROM tenders
            WHERE {where}
            ORDER BY scraped_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    return {
        "tenders": [dict(r._mapping) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/stats/overview")
async def get_tender_stats(
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """Aggregate stats from the real tenders table."""
    row = (
        await session.execute(
            text("""
                SELECT
                    COUNT(*)                                                    AS total,
                    COUNT(*) FILTER (WHERE status = 'active')                  AS active,
                    COUNT(*) FILTER (WHERE status = 'closed')                  AS closed,
                    COUNT(*) FILTER (
                        WHERE bid_end_date BETWEEN CURRENT_DATE
                          AND CURRENT_DATE + INTERVAL '7 days'
                    )                                                           AS closing_soon,
                    ROUND(AVG(estimated_value) FILTER (
                        WHERE estimated_value IS NOT NULL
                    )::numeric, 2)                                              AS avg_value,
                    COUNT(DISTINCT portal)                                      AS portals_count
                FROM tenders
            """)
        )
    ).mappings().one()

    return {"data": dict(row)}


@router.get("/closing-soon/list")
async def get_closing_soon(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """Tenders closing within N days — tries tenders_closing_soon first, falls back to tenders."""
    # Check if the dedicated closing-soon table exists
    table_check = (
        await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name   = 'tenders_closing_soon'
                )
            """)
        )
    ).scalar()

    source_table = "tenders_closing_soon" if table_check else "tenders"

    rows = await session.execute(
        text(f"""
            SELECT {TENDER_SELECT}
            FROM {source_table}
            WHERE bid_end_date BETWEEN CURRENT_DATE
              AND CURRENT_DATE + :days * INTERVAL '1 day'
            ORDER BY bid_end_date ASC
            LIMIT :limit
        """),
        {"days": days, "limit": limit},
    )

    tenders = [dict(r._mapping) for r in rows]
    return {"data": tenders, "count": len(tenders), "days": days}


@router.get("/alerts/list")
async def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_db_session),
    company_id=Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """Fetch alerts for the current company."""
    conditions = ["company_id = :company_id"]
    params: dict = {"company_id": str(company_id), "limit": limit}

    if unread_only:
        conditions.append("is_read = FALSE")

    where = " AND ".join(conditions)

    rows = await session.execute(
        text(f"""
            SELECT
                id::text        AS id,
                company_id::text,
                tender_id::text,
                alert_type,
                message,
                is_read,
                is_sent,
                created_at::text,
                read_at::text
            FROM alerts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        params,
    )

    return {"data": [dict(r._mapping) for r in rows]}


# ── Parameterised route LAST — avoids swallowing the routes above ─────────────

@router.get("/{tender_id}")
async def get_tender(
    tender_id: str,
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    _trace_id: str = Depends(get_trace_id),
):
    """Fetch a single tender by its UUID or scraper tender_id."""
    # Try UUID match first, then scraper string id
    row = (
        await session.execute(
            text(f"""
                SELECT {TENDER_SELECT}
                FROM tenders
                WHERE id::text = :tid
                   OR tender_id = :tid
                LIMIT 1
            """),
            {"tid": tender_id},
        )
    ).mappings().first()

    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tender not found")

    return {"data": dict(row)}
