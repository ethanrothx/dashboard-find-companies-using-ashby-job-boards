"""Scrape Ashby job boards for companies discovered by the main pipeline.

Ingests the discovery tool's ``verified_ashby_slugs.json`` (or CSV), fetches each
company's open roles from Ashby's public job-board GraphQL API, aggregates them
into per-company attributes, and emits sortable CSV/JSON plus an interactive HTML
dashboard.
"""

from .models import CompanyJobs, JobPosting

__all__ = ["CompanyJobs", "JobPosting"]
