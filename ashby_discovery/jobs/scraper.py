from __future__ import annotations

import asyncio
from typing import Callable, Iterable, Optional

from .aggregate import aggregate_company, error_company
from .client import AshbyJobsClient
from .models import CompanyJobs


async def scrape_companies(
    companies: Iterable[dict],
    *,
    client: Optional[AshbyJobsClient] = None,
    on_progress: Optional[Callable[[CompanyJobs], None]] = None,
    **client_kwargs,
) -> list[CompanyJobs]:
    """Fetch and aggregate Ashby job boards for each discovered company.

    ``companies`` are dicts from the discovery output (need at least ``slug``;
    ``inferred_company_name`` and ``ashby_url`` are used when present).
    """
    owns_client = client is None
    client = client or AshbyJobsClient(**client_kwargs)
    try:
        async def one(company: dict) -> CompanyJobs:
            slug = str(company.get("slug", "")).strip()
            name = str(
                company.get("inferred_company_name") or company.get("company_name") or slug
            ).strip()
            ashby_url = str(
                company.get("ashby_url") or f"https://jobs.ashbyhq.com/{slug}"
            ).strip()
            try:
                board = await client.fetch_board(slug)
                result = aggregate_company(
                    slug=slug, company_name=name, ashby_url=ashby_url, board=board
                )
            except Exception as exc:  # noqa: BLE001 - recorded per-company, never fatal
                result = error_company(
                    slug=slug,
                    company_name=name,
                    ashby_url=ashby_url,
                    error=f"{type(exc).__name__}: {exc}",
                )
            if on_progress is not None:
                on_progress(result)
            return result

        tasks = [asyncio.create_task(one(c)) for c in companies if str(c.get("slug", "")).strip()]
        return await asyncio.gather(*tasks)
    finally:
        if owns_client:
            await client.close()
