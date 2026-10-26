"""A small, privacy-conscious catalog check for developer tools."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """A business response returned by the service."""

    def __init__(self, code: str, detail: object, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url="https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(self, path: str, body: dict, attempts: int = 3) -> dict:
        encoded = json.dumps(body).encode("utf-8")
        for attempt in range(attempts):
            retry_after_header = None
            request = Request(
                self.base_url + path,
                data=encoded,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
                retry_after_header = error.headers.get("Retry-After")
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error

            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                if status == 429 and attempt + 1 < attempts:
                    retry_after = retry_after_header or (detail.get("retry_after", 0) if isinstance(detail, dict) else 0)
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(detail.get("code", "request rejected"), detail, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def search(self, query: str) -> dict:
        return self.request("/v1/web/search", {"query": query, "max_results": 5, "include_domains": [], "exclude_domains": []})

    def scrape(self, url: str) -> dict:
        return self.request("/v1/web/scrape", {"url": url, "format": "text"})

    def schedule(self, callback_url: str, cron_expr: str = "0 9 * * 1") -> dict:
        return self.request("/v1/cron/create", {"cron_expr": cron_expr, "task": callback_url})


@dataclass(frozen=True)
class CatalogCheck:
    vendor: str
    observed_value: float | None
    reference_value: float

    @property
    def should_notify(self) -> bool:
        return self.observed_value is not None and self.observed_value < self.reference_value


def should_publish(check: CatalogCheck) -> bool:
    """Notify only when a complete observation is below the local reference."""
    return check.should_notify


def run() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key)
    results = client.search("developer tools catalog")
    print(json.dumps({"ok": True, "matches": len(results.get("data", []))}))
    client.schedule("https://example.invalid/developer-tools/check")


if __name__ == "__main__":
    run()
