"""Localized user-friendly error classes for DocuMaker DZ."""

from __future__ import annotations

from typing import Any


class DocuMakerError(Exception):
    """Base application error carrying a localization key instead of raw stack traces."""

    def __init__(
        self,
        loc_key: str,
        technical_detail: str = "",
        step: int | None = None,
        **format_args: Any,
    ) -> None:
        self.loc_key = loc_key
        self.technical_detail = technical_detail or loc_key
        self.step = step
        self.format_args = format_args
        super().__init__(self.technical_detail)

    def user_message(self, loc_manager: Any) -> str:
        return str(loc_manager.t(self.loc_key, **self.format_args))


class CancelledError(DocuMakerError):
    def __init__(self, step: int | None = None) -> None:
        super().__init__("err.cancelled", "Job cancelled by user", step=step)
