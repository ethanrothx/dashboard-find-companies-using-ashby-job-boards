from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from .output import load_companies, save_outputs
from .report import save_report
from .scraper import scrape_companies


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ashby_discovery.jobs",
        description=(
            "Scrape open roles for companies discovered by the Ashby discovery "
            "pipeline, then emit sortable CSV/JSON and an interactive HTML dashboard."
        ),
    )
    p.add_argument(
        "--input",
        type=Path,
        default=Path("output/verified_ashby_slugs.json"),
        help="Discovery output to ingest (.json or .csv). Default: output/verified_ashby_slugs.json",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for scraped outputs. Default: output",
    )
    p.add_argument(
        "--base-name",
        default="ashby_companies",
        help="Base name for output files. Default: ashby_companies",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only scrape the first N companies (0 = all). Useful for smoke tests.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Max simultaneous requests to the Ashby API. Default: 8",
    )
    p.add_argument(
        "--request-delay",
        type=float,
        default=0.25,
        help="Min seconds between requests (rate limit). Default: 0.25",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-request timeout in seconds. Default: 20",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries per request on transient errors. Default: 3",
    )
    p.add_argument("--no-html", action="store_true", help="Skip the HTML dashboard.")
    p.add_argument("--quiet", action="store_true", help="Suppress per-company progress.")
    return p


async def _run(args: argparse.Namespace) -> int:
    if not args.input.exists():
        print(f"error: input file not found: {args.input}")
        print("Run the discovery pipeline first, or pass --input.")
        return 2

    companies = load_companies(args.input)
    if args.limit > 0:
        companies = companies[: args.limit]
    if not companies:
        print(f"error: no companies found in {args.input}")
        return 2

    print(f"Scraping Ashby job boards for {len(companies)} companies…")

    done = 0
    total = len(companies)

    def on_progress(result) -> None:
        nonlocal done
        done += 1
        if not args.quiet:
            status = result.fetch_status
            detail = (
                f"{result.job_count} jobs" if status == "OK" else status.lower()
            )
            print(f"  [{done}/{total}] {result.company_name}: {detail}")

    results = await scrape_companies(
        companies,
        on_progress=on_progress,
        timeout_seconds=args.timeout,
        max_connections=args.concurrency,
        retries=args.retries,
        min_interval_seconds=args.request_delay,
    )
    # Preserve input ordering for deterministic output.
    order = {str(c.get("slug", "")).strip(): i for i, c in enumerate(companies)}
    results.sort(key=lambda r: order.get(r.slug, 1 << 30))

    paths = save_outputs(results, args.output_dir, base_name=args.base_name)
    written = [paths["companies_csv"], paths["companies_json"], paths["jobs_csv"]]

    if not args.no_html:
        html_path = args.output_dir / f"{args.base_name}_dashboard.html"
        save_report(
            results,
            html_path,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            source=str(args.input),
        )
        written.append(html_path)

    hiring = sum(1 for r in results if r.job_count > 0)
    total_jobs = sum(r.job_count for r in results)
    errors = sum(1 for r in results if r.fetch_status == "ERROR")

    print()
    print(f"Companies scraped:   {len(results)}")
    print(f"Actively hiring:     {hiring}")
    print(f"Total open roles:    {total_jobs}")
    print(f"Fetch errors:        {errors}")
    print("Wrote:")
    for path in written:
        print(f"  {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(_run(args))
