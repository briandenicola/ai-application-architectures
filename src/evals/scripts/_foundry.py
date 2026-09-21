"""Thin REST client for the Microsoft Foundry data plane.

Deliberately NOT an SDK wrapper. The demo's claim is that Foundry evaluates the
agent — Foundry calls it, Foundry scores it, Foundry stores the result. A local
SDK that computes scores on the SE's laptop would prove the SDK works, not the
platform. So every call here is plain HTTP against a documented endpoint, and
the only Azure library involved is azure-identity, purely to mint a token.

Two route families, with different versioning rules:
  * /openai/v1/*  — path-versioned, NO api-version query parameter
  * everything else (/datasets, /evaluators) — requires ?api-version=

Getting that wrong returns a confusing 404, so it is handled centrally.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from _common import get_credential

API_VERSION = "2025-11-15-preview"

# Evaluator authoring and rubric evaluators are preview features. Without this
# header the routes exist but reject the request.
PREVIEW_HEADER = {"Foundry-Features": "Evaluations=V1Preview"}

# Foundry project data-plane tokens are scoped to ai.azure.com, NOT to
# cognitiveservices.azure.com. The latter yields a 401 that looks like an RBAC
# problem and sends you hunting for the wrong thing.
SCOPE = "https://ai.azure.com/.default"


class FoundryError(RuntimeError):
    """A Foundry REST call failed. Carries the body, because the body is where
    the actual reason lives — the status code alone is rarely enough."""


class FoundryClient:
    def __init__(self, endpoint: str, timeout: float = 120.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._credential = get_credential()
        self._client = httpx.Client(timeout=timeout)

    def _token(self) -> str:
        return self._credential.get_token(SCOPE).token

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        preview: bool = False,
        absolute_url: str | None = None,
    ) -> dict[str, Any]:
        url = absolute_url or f"{self.endpoint}/{path.lstrip('/')}"
        # A continuation link is already complete. Passing params alongside it
        # makes httpx REPLACE its query string, dropping api-version and the
        # cursor — which fails as "Missing required query parameter".
        query = {} if absolute_url else dict(params or {})
        if not absolute_url and not path.lstrip("/").startswith("openai/"):
            query.setdefault("api-version", API_VERSION)

        headers = {"Authorization": f"Bearer {self._token()}"}
        if preview:
            headers.update(PREVIEW_HEADER)

        # `params={}` still makes httpx rewrite the query string, so an empty
        # mapping must become None or a continuation URL loses its parameters.
        response = self._client.request(
            method, url, json=json_body, params=query or None, headers=headers
        )
        if response.status_code >= 400:
            raise FoundryError(
                f"{method} {url} -> {response.status_code}\n{response.text[:2000]}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw": response.text}

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("PATCH", path, **kwargs)

    def paged(self, path: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Collect every page, regardless of which paging dialect the route speaks.

        Two coexist on this data plane: Azure-style (`value` + `nextLink`) on
        /evaluators and /datasets, and OpenAI-style (`data` + `has_more` + cursor)
        on /agents and /openai/*. Handling only one returns an empty list from the
        other — which looks exactly like "the resource does not exist".

        Paging is not optional here: the evaluator catalog pages at 10 and would
        silently omit most of itself, including groundedness.
        """
        items: list[dict[str, Any]] = []
        page = self.get(path, **kwargs)
        while True:
            if "value" in page:
                items.extend(page.get("value", []))
                next_link = page.get("nextLink")
                if not next_link:
                    return items
                page = self.request("GET", "", absolute_url=next_link, **kwargs)
                continue

            batch = page.get("data", [])
            items.extend(batch)
            if not page.get("has_more") or not batch:
                return items
            params = dict(kwargs.pop("params", None) or {})
            params["after"] = page.get("last_id") or batch[-1].get("id")
            page = self.get(path, params=params, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FoundryClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
