from __future__ import annotations

import json

import pytest

from ashby_discovery.jobs.aggregate import aggregate_company, error_company
from ashby_discovery.jobs.client import RawBoard, slug_variants
from ashby_discovery.jobs.output import company_rows, job_rows
from ashby_discovery.jobs.report import render_report
from ashby_discovery.jobs.scraper import scrape_companies


def _board(resolved="acme"):
    teams = [
        {"id": "t1", "name": "Engineering"},
        {"id": "t2", "name": "Sales"},
    ]
    postings = [
        {"title": "Backend Engineer", "teamId": "t1", "locationName": "Remote - US",
         "employmentType": "FullTime", "secondaryLocations": [{"locationName": "Canada"}]},
        {"title": "Frontend Engineer", "teamId": "t1", "locationName": "New York",
         "employmentType": "FullTime", "secondaryLocations": []},
        {"title": "Account Executive", "teamId": "t2", "locationName": "New York",
         "employmentType": "FullTime", "secondaryLocations": []},
    ]
    return RawBoard(resolved, teams, postings)


def test_slug_variants_tries_capitalized() -> None:
    assert slug_variants("ashby") == ["ashby", "Ashby"]
    assert slug_variants("Ashby") == ["Ashby"]
    assert slug_variants("") == [""]


def test_aggregate_company_rolls_up_attributes() -> None:
    c = aggregate_company(
        slug="acme", company_name="Acme", ashby_url="https://jobs.ashbyhq.com/acme",
        board=_board(),
    )
    assert c.job_count == 3
    assert c.remote_job_count == 1  # "Remote - US"
    assert c.top_location == "New York"  # appears twice
    assert c.location_count == 2
    assert c.top_department == "Engineering"
    assert c.department_count == 2
    assert c.employment_types == {"FullTime": 3}
    assert c.fetch_status == "OK"


def test_aggregate_empty_board_marks_empty() -> None:
    c = aggregate_company(
        slug="x", company_name="X", ashby_url="u", board=RawBoard("x", [], []),
    )
    assert c.fetch_status == "EMPTY"
    assert c.job_count == 0


def test_output_rows_are_flat_and_serializable() -> None:
    c = aggregate_company(slug="acme", company_name="Acme", ashby_url="u", board=_board())
    crows = company_rows([c])
    jrows = job_rows([c])
    assert crows[0]["job_count"] == 3
    assert crows[0]["employment_types"] == "FullTime:3"
    assert len(jrows) == 3
    assert jrows[0]["is_remote"] is True
    json.dumps(crows)  # must be serializable
    json.dumps(jrows)


def test_render_report_embeds_data_and_is_self_contained() -> None:
    c = aggregate_company(slug="acme", company_name="Acme", ashby_url="u", board=_board())
    err = error_company(slug="bad", company_name="Bad", ashby_url="u", error="boom")
    html = render_report([c, err], generated_at="2026-07-02", source="x.json")
    assert "<!doctype html>" in html
    assert "Backend Engineer" in html
    assert "Acme" in html
    # No external resource references (CSP-safe / offline-usable).
    assert "cdn" not in html.lower()
    assert "<script src" not in html.lower()
    assert 'link rel="stylesheet"' not in html.lower()


class _FakeClient:
    def __init__(self, boards):
        self.boards = boards

    async def fetch_board(self, slug):
        if self.boards.get(slug) == "raise":
            raise RuntimeError("network down")
        return self.boards.get(slug, RawBoard(slug, [], []))

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_scrape_companies_handles_ok_empty_and_error() -> None:
    companies = [
        {"slug": "acme", "inferred_company_name": "Acme", "ashby_url": "u1"},
        {"slug": "empty", "inferred_company_name": "Empty", "ashby_url": "u2"},
        {"slug": "boom", "inferred_company_name": "Boom", "ashby_url": "u3"},
        {"slug": ""},  # skipped
    ]
    client = _FakeClient({"acme": _board("acme"), "boom": "raise"})
    results = await scrape_companies(companies, client=client)
    by_slug = {r.slug: r for r in results}
    assert len(results) == 3  # blank slug skipped
    assert by_slug["acme"].fetch_status == "OK"
    assert by_slug["acme"].job_count == 3
    assert by_slug["empty"].fetch_status == "EMPTY"
    assert by_slug["boom"].fetch_status == "ERROR"
    assert "network down" in by_slug["boom"].notes
