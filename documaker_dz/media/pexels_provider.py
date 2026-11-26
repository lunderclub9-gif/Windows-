"""Pexels Image & Video provider with sequential streaming download and local disk cache."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ..core.errors import DocuMakerError
from ..core.http_client import HttpNetworkError, download_file, request_json
from ..core.models import MediaCandidate
from .base import ImageProvider, VideoProvider


class PexelsMediaProvider(ImageProvider, VideoProvider):
    name = "pexels"
    BASE_URL = "https://api.pexels.com"

    def __init__(self, api_key: str, cache_dir: Path | None = None) -> None:
        self.api_key = api_key.strip()
        self.cache_dir = cache_dir

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise DocuMakerError("err.missing_pexels_key", "Missing Pexels API key")
        return {"Authorization": self.api_key}

    @staticmethod
    def _score_candidate(width: int, height: int, is_video: bool, duration: float = 0.0) -> float:
        score = 0.0
        if width >= height:
            score += 40.0
        if width >= 1280:
            score += 25.0
        if is_video and 4.0 <= duration <= 35.0:
            score += 20.0
        return score

    def search_images(self, query: str, per_page: int = 4) -> list[MediaCandidate]:
        try:
            resp = request_json(
                "GET",
                f"{self.BASE_URL}/v1/search",
                headers=self._headers(),
                params={"query": query, "per_page": per_page, "orientation": "landscape"},
                timeout=30.0,
            )
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc

        if resp.status_code in (401, 403):
            raise DocuMakerError("err.invalid_pexels_key", f"Pexels HTTP {resp.status_code}")
        if resp.status_code == 429:
            raise DocuMakerError("err.rate_limit", "Pexels rate limit")
        if resp.status_code >= 400:
            raise DocuMakerError("err.generic", f"Pexels image search failed: {resp.status_code}")

        photos = resp.json().get("photos", [])
        results: list[MediaCandidate] = []
        for p in photos:
            w = int(p.get("width", 0))
            h = int(p.get("height", 0))
            src = p.get("src", {})
            dl_url = src.get("large2x") or src.get("large") or src.get("original") or ""
            if not dl_url:
                continue
            photographer = p.get("photographer", "Pexels Contributor")
            results.append(
                MediaCandidate(
                    provider="pexels",
                    media_type="image",
                    media_id=str(p.get("id", "")),
                    url=str(p.get("url", "")),
                    download_url=dl_url,
                    thumbnail_url=str(src.get("medium") or src.get("small") or dl_url),
                    width=w,
                    height=h,
                    license_name="Pexels License (Free for commercial/editorial use)",
                    attribution=f"Photo by {photographer} on Pexels",
                    source_page=str(p.get("url", "")),
                    score=self._score_candidate(w, h, is_video=False),
                )
            )
        results.sort(key=lambda c: c.score, reverse=True)
        return results

    def search_videos(self, query: str, per_page: int = 4) -> list[MediaCandidate]:
        try:
            resp = request_json(
                "GET",
                f"{self.BASE_URL}/videos/search",
                headers=self._headers(),
                params={"query": query, "per_page": per_page, "orientation": "landscape"},
                timeout=30.0,
            )
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc

        if resp.status_code in (401, 403):
            raise DocuMakerError("err.invalid_pexels_key", f"Pexels HTTP {resp.status_code}")
        if resp.status_code == 429:
            raise DocuMakerError("err.rate_limit", "Pexels rate limit")
        if resp.status_code >= 400:
            raise DocuMakerError("err.generic", f"Pexels video search failed: {resp.status_code}")

        videos = resp.json().get("videos", [])
        results: list[MediaCandidate] = []
        for v in videos:
            files = v.get("video_files", [])
            mp4_files = [f for f in files if f.get("file_type") == "video/mp4" and int(f.get("width", 0)) >= 640]
            if not mp4_files:
                continue
            mp4_files.sort(key=lambda f: abs(int(f.get("width", 1280)) - 1280))
            best = mp4_files[0]
            w = int(best.get("width", 1280))
            h = int(best.get("height", 720))
            dur = float(v.get("duration", 0.0))
            user_name = (v.get("user") or {}).get("name", "Pexels Contributor")
            results.append(
                MediaCandidate(
                    provider="pexels",
                    media_type="video",
                    media_id=str(v.get("id", "")),
                    url=str(v.get("url", "")),
                    download_url=str(best.get("link", "")),
                    thumbnail_url=str(v.get("image", "")),
                    width=w,
                    height=h,
                    duration=dur,
                    license_name="Pexels License (Free for commercial/editorial use)",
                    attribution=f"Video by {user_name} on Pexels",
                    source_page=str(v.get("url", "")),
                    score=self._score_candidate(w, h, is_video=True, duration=dur),
                )
            )
        results.sort(key=lambda c: c.score, reverse=True)
        return results

    def download_candidate(self, candidate: MediaCandidate, dest_dir: Path, filename_prefix: str) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        ext = ".mp4" if candidate.media_type == "video" else ".jpg"
        dest_path = dest_dir / f"{filename_prefix}{ext}"

        url_hash = hashlib.sha1(candidate.download_url.encode("utf-8")).hexdigest()[:16]
        cache_path = (self.cache_dir / f"pexels_{url_hash}{ext}") if self.cache_dir else None
        if cache_path and cache_path.exists() and cache_path.stat().st_size > 1024:
            shutil.copy2(cache_path, dest_path)
            candidate.local_path = str(dest_path)
            return dest_path

        try:
            status = download_file(candidate.download_url, dest_path, timeout=90.0)
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc
        if status >= 400:
            raise DocuMakerError("err.generic", f"Media download HTTP {status}")

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest_path, cache_path)
        candidate.local_path = str(dest_path)
        return dest_path

    def test_connection(self) -> tuple[bool, str]:
        try:
            items = self.search_images("nature", per_page=1)
            return len(items) > 0, "OK"
        except DocuMakerError as exc:
            return False, exc.technical_detail
