"""Resilient HTTP client helper using httpx if available, with stdlib urllib fallback."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class HttpNetworkError(Exception):
    pass


@dataclass
class HttpResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        return json.loads(self.text)


def request_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> HttpResponse:
    req_headers = dict(headers or {})
    full_url = url
    if params:
        qs = urllib.parse.urlencode(params)
        sep = "&" if "?" in full_url else "?"
        full_url = f"{full_url}{sep}{qs}"

    try:
        import httpx  # type: ignore

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.request(method, url, headers=req_headers, params=params, json=json_body)
            return HttpResponse(status_code=resp.status_code, text=resp.text)
    except ImportError:
        pass
    except Exception as exc:
        raise HttpNetworkError(str(exc)) from exc

    data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    if data is not None and "Content-Type" not in req_headers:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(full_url, data=data, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return HttpResponse(status_code=resp.status, text=raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return HttpResponse(status_code=exc.code, text=raw)
    except urllib.error.URLError as exc:
        raise HttpNetworkError(str(exc.reason)) from exc


def download_file(
    url: str,
    dest_path: Path,
    headers: dict[str, str] | None = None,
    timeout: float = 90.0,
) -> int:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req_headers = dict(headers or {})

    try:
        import httpx  # type: ignore

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", url, headers=req_headers) as resp:
                if resp.status_code >= 400:
                    return resp.status_code
                with dest_path.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        fh.write(chunk)
                return resp.status_code
    except ImportError:
        pass
    except Exception as exc:
        raise HttpNetworkError(str(exc)) from exc

    req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with dest_path.open("wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        raise HttpNetworkError(str(exc.reason)) from exc
