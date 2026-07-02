from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from ..http_client import AsyncRateLimiter

# Ashby's public, unauthenticated job-board GraphQL endpoint. The same endpoint
# powers every hosted board at https://jobs.ashbyhq.com/{slug}.
GRAPHQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"

_QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    teams { id name parentTeamId }
    jobPostings {
      id
      title
      teamId
      locationName
      employmentType
      secondaryLocations { locationName }
    }
  }
}
"""


class RawBoard:
    """Parsed GraphQL payload for one job board."""

    def __init__(self, resolved_slug: str, teams: list[dict], postings: list[dict]) -> None:
        self.resolved_slug = resolved_slug
        self.team_names = {t["id"]: t.get("name") or "" for t in teams}
        self.postings = postings

    def __len__(self) -> int:  # number of postings
        return len(self.postings)


def slug_variants(slug: str) -> list[str]:
    """Ashby org names are case-sensitive; the discovered slug may not match.

    Try the slug as-is first, then a capitalized variant, deduped. This recovers
    boards like ``Ashby`` when the discovered URL was ``/ashby``.
    """
    variants = [slug]
    if slug:
        cap = slug[0].upper() + slug[1:]
        if cap not in variants:
            variants.append(cap)
    return variants


class AshbyJobsClient:
    """Fetches open roles for a given board slug from the public Ashby API."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_connections: int = 8,
        retries: int = 3,
        min_interval_seconds: float = 0.25,
        user_agent: str = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.retries = max(retries, 1)
        self.rate_limiter = AsyncRateLimiter(min_interval_seconds)
        self.semaphore = asyncio.Semaphore(max_connections)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_connections,
            ),
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "AshbyJobsClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _post(self, organization: str) -> Optional[dict]:
        """POST one GraphQL query. Returns the ``jobBoard`` object or None."""
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "query": _QUERY,
            "variables": {"organizationHostedJobsPageName": organization},
        }
        last_error: Exception | None = None
        async with self.semaphore:
            for attempt in range(1, self.retries + 1):
                try:
                    await self.rate_limiter.wait()
                    resp = await self.client.post(GRAPHQL_URL, json=payload)
                    if resp.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            "server error", request=resp.request, response=resp
                        )
                    data = resp.json()
                    if data.get("errors"):
                        # A schema/validation error will not recover on retry.
                        raise ValueError(data["errors"][0].get("message", "graphql error"))
                    return data.get("data", {}).get("jobBoard")
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    if attempt < self.retries:
                        await asyncio.sleep(1.5 * attempt)
        if last_error is not None:
            raise last_error
        return None

    async def fetch_board(self, slug: str) -> RawBoard:
        """Fetch a board, trying case variants until one returns postings.

        Raises the last exception if every variant errored. Returns an empty
        RawBoard (len 0) when the board exists but has no open roles.
        """
        last_error: Exception | None = None
        empty_hit: Optional[RawBoard] = None
        for variant in slug_variants(slug):
            try:
                board = await self._post(variant)
            except Exception as exc:  # noqa: BLE001 - propagated below if all fail
                last_error = exc
                continue
            if board is None:
                empty_hit = empty_hit or RawBoard(variant, [], [])
                continue
            postings = board.get("jobPostings") or []
            teams = board.get("teams") or []
            raw = RawBoard(variant, teams, postings)
            if postings:
                return raw
            empty_hit = empty_hit or raw
        if empty_hit is not None:
            return empty_hit
        if last_error is not None:
            raise last_error
        return RawBoard(slug, [], [])
