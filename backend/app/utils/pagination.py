"""Pagination listes — format compatible frontend (`items`) + bloc `pagination`."""
from __future__ import annotations

from flask import request


def parse_pagination(
    *,
    default_per_page: int = 25,
    max_per_page: int = 100,
) -> tuple[int, int]:
    """Lit `page` / `per_page` depuis la query string."""
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", default_per_page))
    except (TypeError, ValueError):
        per_page = default_per_page
    page = max(page, 1)
    per_page = min(max(per_page, 1), max_per_page)
    return page, per_page


def paginate_query(query, page: int, per_page: int):
    """Retourne (items, total, pages)."""
    total = query.count()
    pages = max((total + per_page - 1) // per_page, 1) if total else 0
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, pages


def pagination_payload(items, *, page: int, per_page: int, total: int, pages: int) -> dict:
    """Envelope liste paginée (rétro-compatible avec `items` / `total`)."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        },
    }


def empty_pagination(*, page: int = 1, per_page: int = 25) -> dict:
    return pagination_payload([], page=page, per_page=per_page, total=0, pages=0)
