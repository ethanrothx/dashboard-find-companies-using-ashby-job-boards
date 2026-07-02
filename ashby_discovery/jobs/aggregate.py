from __future__ import annotations

from collections import Counter

from .client import RawBoard
from .models import CompanyJobs, JobPosting


def _clean(value: object) -> str:
    return str(value).strip() if value is not None else ""


def build_postings(slug: str, company_name: str, board: RawBoard) -> list[JobPosting]:
    postings: list[JobPosting] = []
    for raw in board.postings:
        secondary = tuple(
            _clean(loc.get("locationName"))
            for loc in (raw.get("secondaryLocations") or [])
            if _clean(loc.get("locationName"))
        )
        postings.append(
            JobPosting(
                company_slug=slug,
                company_name=company_name,
                title=_clean(raw.get("title")),
                location=_clean(raw.get("locationName")),
                employment_type=_clean(raw.get("employmentType")),
                department=_clean(board.team_names.get(raw.get("teamId"))),
                secondary_locations=secondary,
            )
        )
    return postings


def aggregate_company(
    *,
    slug: str,
    company_name: str,
    ashby_url: str,
    board: RawBoard,
    fetch_status: str = "OK",
    notes: str = "",
) -> CompanyJobs:
    """Roll a fetched board up into sortable per-company attributes."""
    postings = build_postings(slug, company_name, board)

    location_counter: Counter[str] = Counter(p.location for p in postings if p.location)
    department_counter: Counter[str] = Counter(p.department for p in postings if p.department)
    employment_types: Counter[str] = Counter(
        p.employment_type for p in postings if p.employment_type
    )

    top_location = location_counter.most_common(1)[0][0] if location_counter else ""
    top_department = department_counter.most_common(1)[0][0] if department_counter else ""

    status = fetch_status
    if status == "OK" and not postings:
        status = "EMPTY"

    return CompanyJobs(
        slug=slug,
        company_name=company_name,
        ashby_url=ashby_url,
        fetch_status=status,
        resolved_slug=board.resolved_slug,
        job_count=len(postings),
        remote_job_count=sum(1 for p in postings if p.is_remote),
        location_count=len(location_counter),
        department_count=len(department_counter),
        top_location=top_location,
        top_department=top_department,
        locations=[loc for loc, _ in location_counter.most_common()],
        departments=[dep for dep, _ in department_counter.most_common()],
        employment_types=dict(employment_types),
        notes=notes,
        postings=postings,
    )


def error_company(*, slug: str, company_name: str, ashby_url: str, error: str) -> CompanyJobs:
    return CompanyJobs(
        slug=slug,
        company_name=company_name,
        ashby_url=ashby_url,
        fetch_status="ERROR",
        notes=error,
    )
