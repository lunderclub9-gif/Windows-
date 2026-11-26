"""Quality & Licensing Reviewer before final MP4 export."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.errors import DocuMakerError
from ..core.models import Project


@dataclass
class QualityReport:
    ok: bool = True
    warnings: list[str] = field(default_factory=list)
    missing_license_scene_ids: list[int] = field(default_factory=list)


class QualityReviewer:
    """Validates copyright licensing, attribution metadata, and research warnings."""

    def review_before_export(self, project: Project) -> QualityReport:
        report = QualityReport()
        if not project.scenes:
            raise DocuMakerError("err.generic", "No scenes in project to export", step=9)

        for scene in project.scenes:
            if not scene.selected_media or not scene.selected_media.local_path:
                raise DocuMakerError(
                    "err.no_visuals_found",
                    f"Missing visual media for scene {scene.id}",
                    step=9,
                    scene=scene.id,
                )
            lic = (scene.selected_media.license_name or "").strip().lower()
            if not lic or lic in ("unknown", "unverified"):
                report.missing_license_scene_ids.append(scene.id)
                raise DocuMakerError(
                    "err.unknown_license",
                    f"Unknown license for scene {scene.id}",
                    step=9,
                    scene=scene.id,
                )

        if project.research.sensitive_topics:
            report.warnings.append(
                f"Sensitive topics flagged: {', '.join(project.research.sensitive_topics)}"
            )
        if not project.research.sources:
            report.warnings.append("No external citations attached to research brief.")
        return report
