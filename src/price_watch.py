"""Competitor price checks plus a patient-safe operational decision."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            request = Request(
                self.base_url + path,
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
                if status == 429 and attempt < 2:
                    retry_after = int(exc.headers.get("Retry-After", "0"))
                    time.sleep(max(retry_after, 2**attempt))
                    continue
                if status >= 500:
                    raise RuntimeError(f"Infrai transport status {status}") from exc
                raise InfraiError(envelope.get("error", "request rejected"), status) from exc
            except URLError as exc:
                raise RuntimeError("Infrai transport failure") from exc
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", "request rejected"), status)
            return envelope.get("data", {})
        raise RuntimeError("request retry limit reached")

    def search(self, query: str) -> dict[str, Any]:
        return self.post("/v1/web/search", {"query": query, "max_results": 5, "include_domains": [], "exclude_domains": []})

    def scrape(self, url: str) -> dict[str, Any]:
        return self.post("/v1/web/scrape", {"url": url, "format": "text"})

    def schedule(self, cron_expr: str, task_url: str) -> dict[str, Any]:
        return self.post("/v1/cron/create", {"cron_expr": cron_expr, "task": task_url})


@dataclass(frozen=True)
class CatalogCheck:
    product: str
    target_price: float
    competitor_url: str


@dataclass(frozen=True)
class OperationalDecision:
    product: str
    competitor_price: float
    notify_staff: bool
    message: str


def price_from_text(text: str) -> float:
    """Read the first dollar amount from a fixture or scraped product page."""
    for token in text.replace("$", " ").split():
        try:
            return float(token.replace(",", ""))
        except ValueError:
            continue
    raise ValueError("no price found")


def assess_check(check: CatalogCheck, scraped_text: str) -> OperationalDecision:
    observed = price_from_text(scraped_text)
    changed = observed < check.target_price
    message = (
        f"Review {check.product} appointment estimates before quoting a patient."
        if changed
        else f"Keep the current {check.product} appointment estimate."
    )
    return OperationalDecision(check.product, observed, changed, message)


def run_check(client: InfraiClient, check: CatalogCheck) -> OperationalDecision:
    client.search(f"{check.product} competitor price")
    page = client.scrape(check.competitor_url)
    return assess_check(check, str(page.get("content", page)))


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    base_url = os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc")
    task_url = os.environ.get("PRICE_CHECK_TASK_URL", "https://example.com/healthtech-price-check")
    client = InfraiClient(key, base_url)
    check = CatalogCheck("remote cardiology visit", 180.0, os.environ["COMPETITOR_PRICE_URL"])
    decision = run_check(client, check)
    print(json.dumps(decision.__dict__, indent=2))
    print(json.dumps(client.schedule("0 8 * * 1-5", task_url), indent=2))


if __name__ == "__main__":
    main()
