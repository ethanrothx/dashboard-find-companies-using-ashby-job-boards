from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .models import CompanyJobs

COMPANY_FIELDS = [
    "slug",
    "company_name",
    "ashby_url",
    "job_count",
    "remote_job_count",
    "location_count",
    "department_count",
    "top_location",
    "top_department",
    "employment_types",
    "locations",
    "departments",
    "fetch_status",
    "resolved_slug",
    "notes",
]

JOB_FIELDS = [
    "company_slug",
    "company_name",
    "title",
    "location",
    "is_remote",
    "employment_type",
    "department",
    "secondary_locations",
]


def load_companies(input_path: Path) -> list[dict]:
    """Load discovered companies from the pipeline's JSON or CSV output."""
    text = input_path.read_text(encoding="utf-8")
    if input_path.suffix.lower() == ".json":
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("results", [])
    with input_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def company_rows(companies: Iterable[CompanyJobs]) -> list[dict]:
    return [c.to_row() for c in companies]


def job_rows(companies: Iterable[CompanyJobs]) -> list[dict]:
    rows: list[dict] = []
    for company in companies:
        for p in company.postings:
            rows.append(
                {
                    "company_slug": p.company_slug,
                    "company_name": p.company_name,
                    "title": p.title,
                    "location": p.location,
                    "is_remote": p.is_remote,
                    "employment_type": p.employment_type,
                    "department": p.department,
                    "secondary_locations": " | ".join(p.secondary_locations),
                }
            )
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def save_outputs(
    companies: list[CompanyJobs],
    output_dir: Path,
    *,
    base_name: str = "ashby_companies",
) -> dict[str, Path]:
    """Write per-company CSV/JSON and a flat per-job CSV. Returns written paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    crows = company_rows(companies)
    jrows = job_rows(companies)

    companies_csv = output_dir / f"{base_name}.csv"
    companies_json = output_dir / f"{base_name}.json"
    jobs_csv = output_dir / f"{base_name}_jobs.csv"

    _write_csv(companies_csv, COMPANY_FIELDS, crows)
    with companies_json.open("w", encoding="utf-8") as fh:
        json.dump(crows, fh, indent=2, ensure_ascii=False)
    _write_csv(jobs_csv, JOB_FIELDS, jrows)

    return {
        "companies_csv": companies_csv,
        "companies_json": companies_json,
        "jobs_csv": jobs_csv,
    }
