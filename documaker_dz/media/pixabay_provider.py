"""Pixabay media/music provider and Wikimedia Commons public-domain search provider."""

from __future__ import annotations

from pathlib import Path

from ..core.errors import DocuMakerError
from ..core.http_client import HttpNetworkError, download_file, request_json
from ..core.models import MediaCandidate
from .base import ImageProvider, MusicProvider, SearchProvider


class PixabayProvider(ImageProvider, MusicProvider):
    name = "pixabay"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key.strip()

    def search_images(self, query: str, per_page: int = 4) -> list[MediaCandidate]:
        if not self.api_key:
            return []
        try:
            resp = request_json(
                "GET",
                "https://pixabay.com/api/",
                params={
                    "key": self.api_key,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "per_page": per_page,
                    "safesearch": "true",
                },
                timeout=25.0,
            )
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc
        if resp.status_code >= 400:
            return []
        hits = resp.json().get("hits", [])
        out: list[MediaCandidate] = []
        for h in hits:
            dl = h.get("largeImageURL") or h.get("webformatURL")
            if not dl:
                continue
            out.append(
                MediaCandidate(
                    provider="pixabay",
                    media_type="image",
                    media_id=str(h.get("id", "")),
                    url=str(h.get("pageURL", "")),
                    download_url=str(dl),
                    thumbnail_url=str(h.get("previewURL", dl)),
                    width=int(h.get("imageWidth", 1280)),
                    height=int(h.get("imageHeight", 720)),
                    license_name="Pixabay Content License",
                    attribution=f"Image by {h.get('user', 'Pixabay')} on Pixabay",
                    source_page=str(h.get("pageURL", "")),
                    score=35.0,
                )
            )
        return out

    def search_music(self, query: str, mood: str = "") -> list[dict[str, str]]:
        curated = [
            {
                "id": "ambient_calm",
                "title": "Calm Documentary Ambient (Built-in Royalty-Free Pad)",
                "mood": "calm",
                "license": "CC0 / Royalty-Free Local Synthesis",
                "source": "builtin_ambient",
            },
            {
                "id": "oriental_oud_pad",
                "title": "Warm Historical Drone (Built-in Royalty-Free)",
                "mood": "mysterious",
                "license": "CC0 / Royalty-Free Local Synthesis",
                "source": "builtin_historical",
            },
        ]
        q = (query or mood).lower()
        return [c for c in curated if not q or q in c["title"].lower() or q in c["mood"].lower()] or curated

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Missing Pixabay API key"
        try:
            resp = request_json(
                "GET",
                "https://pixabay.com/api/",
                params={"key": self.api_key, "q": "mountain", "per_page": 3},
                timeout=15.0,
            )
            return resp.status_code == 200, f"HTTP {resp.status_code}"
        except HttpNetworkError as exc:
            return False, str(exc)


class WikimediaSearchProvider(SearchProvider):
    """Queries Wikimedia Commons for historical/public-domain images with explicit license checking."""

    name = "wikimedia"
    ALLOWED_LICENSES = ("cc0", "public domain", "cc-by", "cc by")

    def search(self, query: str, limit: int = 4) -> list[MediaCandidate]:
        try:
            resp = request_json(
                "GET",
                "https://commons.wikimedia.org/w/api.php",
                headers={"User-Agent": "DocuMakerDZ/1.0"},
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrnamespace": 6,
                    "gsrsearch": f"{query} filetype:bitmap",
                    "gsrlimit": limit,
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    "format": "json",
                },
                timeout=20.0,
            )
        except HttpNetworkError:
            return []
        if resp.status_code != 200:
            return []
        pages = (resp.json().get("query") or {}).get("pages", {})
        candidates: list[MediaCandidate] = []
        for page in pages.values():
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            meta = info.get("extmetadata") or {}
            lic = ((meta.get("LicenseShortName") or {}).get("value") or "").strip()
            if not any(ok in lic.lower() for ok in self.ALLOWED_LICENSES):
                continue
            dl = info.get("url", "")
            if not dl:
                continue
            candidates.append(
                MediaCandidate(
                    provider="wikimedia",
                    media_type="image",
                    media_id=str(page.get("pageid", "")),
                    url=str(info.get("descriptionurl", dl)),
                    download_url=dl,
                    thumbnail_url=dl,
                    width=int(info.get("width", 0)),
                    height=int(info.get("height", 0)),
                    license_name=lic or "Wikimedia Commons",
                    attribution=str((meta.get("Artist") or {}).get("value") or "Wikimedia Commons"),
                    source_page=str(info.get("descriptionurl", "")),
                    score=30.0,
                )
            )
        return candidates

    @staticmethod
    def download_to(candidate: MediaCandidate, dest_path: Path) -> Path:
        status = download_file(
            candidate.download_url,
            dest_path,
            headers={"User-Agent": "DocuMakerDZ/1.0"},
            timeout=45.0,
        )
        if status >= 400:
            raise DocuMakerError("err.generic", f"Wikimedia download HTTP {status}")
        candidate.local_path = str(dest_path)
        return dest_path
