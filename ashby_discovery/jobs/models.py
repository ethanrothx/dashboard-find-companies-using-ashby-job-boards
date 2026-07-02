from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class JobPosting:
    """A single open role on an Ashby job board."""

    company_slug: str
    company_name: str
    title: str
    location: str
    employment_type: str
    department: str
    secondary_locations: tuple[str, ...] = ()

    @property
    def is_remote(self) -> bool:
        blob = " ".join((self.location, *self.secondary_locations)).lower()
        return "remote" in blob


@dataclass
class CompanyJobs:
    """Per-company roll-up of Ashby job-board data."""

    slug: str
    company_name: str
    ashby_url: str
    fetch_status: str  # OK | EMPTY | ERROR
    resolved_slug: Optional[str] = None  # slug variant that actually returned data
    job_count: int = 0
    remote_job_count: int = 0
    location_count: int = 0
    department_count: int = 0
    top_location: str = ""
    top_department: str = ""
    locations: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    employment_types: dict[str, int] = field(default_factory=dict)
    notes: str = ""
    postings: list[JobPosting] = field(default_factory=list)

    def to_row(self) -> dict:
        """Flat, sortable representation for CSV/JSON/HTML."""
        return {
            "slug": self.slug,
            "company_name": self.company_name,
            "ashby_url": self.ashby_url,
            "job_count": self.job_count,
            "remote_job_count": self.remote_job_count,
            "location_count": self.location_count,
            "department_count": self.department_count,
            "top_location": self.top_location,
            "top_department": self.top_department,
            "employment_types": ", ".join(
                f"{k}:{v}" for k, v in sorted(self.employment_types.items())
            ),
            "locations": " | ".join(self.locations),
            "departments": " | ".join(self.departments),
            "fetch_status": self.fetch_status,
            "resolved_slug": self.resolved_slug or "",
            "notes": self.notes,
        }
