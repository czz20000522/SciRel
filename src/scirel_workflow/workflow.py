"""State transitions for the development SciRel asset workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .models import (
    AutomatedCheckResult,
    CandidatePackage,
    ReleaseManifest,
    ReviewDecision,
    ReviewOutcome,
    StandardizedDraft,
    WorkflowStatus,
)


class WorkflowError(ValueError):
    """Raised when a workflow transition cannot be performed."""


@dataclass
class WorkflowRecord:
    candidate: CandidatePackage
    draft: StandardizedDraft | None = None
    review: ReviewDecision | None = None
    drafts: list[StandardizedDraft] = field(default_factory=list)
    reviews: list[ReviewDecision] = field(default_factory=list)
    automated_results: list[AutomatedCheckResult] = field(default_factory=list)
    release: ReleaseManifest | None = None

    def to_dict(self, *, status: WorkflowStatus) -> dict[str, Any]:
        """Serialize only SciRel-owned workflow state.

        Host scope, job, session and credential data deliberately do not have
        a place in this snapshot.  The host stores the resulting artifact, but
        the payload remains a SciRel domain record.
        """

        return {
            "schema": "scirel.workflow-state.dev",
            "status": status.value,
            "candidate": self.candidate.to_dict(),
            "draft": self.draft.to_dict() if self.draft is not None else None,
            "review": self.review.to_dict() if self.review is not None else None,
            "drafts": [draft.to_dict() for draft in self.drafts],
            "reviews": [review.to_dict() for review in self.reviews],
            "automated_results": [
                result.to_dict() for result in self.automated_results
            ],
            "release": self.release.to_dict() if self.release is not None else None,
        }


class SciRelWorkflow:
    """Small host-independent coordinator for one candidate run."""

    def __init__(self, candidate: CandidatePackage):
        if candidate.status is not WorkflowStatus.CANDIDATE:
            raise WorkflowError("workflow must start with a candidate")
        self.record = WorkflowRecord(candidate=candidate)

    @property
    def status(self) -> WorkflowStatus:
        if self.record.release is not None:
            return WorkflowStatus.RELEASED
        if self.record.review is not None:
            outcome = self.record.review.outcome
            if outcome is ReviewOutcome.APPROVED:
                return WorkflowStatus.APPROVED
            if outcome is ReviewOutcome.NEEDS_EVIDENCE:
                return WorkflowStatus.NEEDS_EVIDENCE
            if outcome is ReviewOutcome.REWORK_REQUESTED:
                return WorkflowStatus.REWORK_REQUESTED
            return WorkflowStatus.REJECTED
        if self.record.draft is not None:
            if self.record.draft.status in (
                WorkflowStatus.REVIEW_PENDING,
                WorkflowStatus.REVIEW_IN_PROGRESS,
            ):
                return self.record.draft.status
            return WorkflowStatus.DRAFT
        candidate = self.record.candidate
        if candidate.automated_ready:
            return WorkflowStatus.AUTOMATED_READY
        if candidate.automated_next_action == "needs_evidence":
            return WorkflowStatus.NEEDS_EVIDENCE
        if candidate.automated_next_action == "rework_requested":
            return WorkflowStatus.REWORK_REQUESTED
        if candidate.automated_next_action == "rejected":
            return WorkflowStatus.REJECTED
        if candidate.automated_failed:
            return WorkflowStatus.AUTOMATED_REJECTED
        if candidate.automated_checks:
            return WorkflowStatus.AUTOMATED_CHECKING
        return WorkflowStatus.CANDIDATE

    def to_dict(self) -> dict[str, Any]:
        """Return a resumable, host-independent workflow snapshot."""

        return self.record.to_dict(status=self.status)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SciRelWorkflow":
        """Restore a workflow snapshot previously produced by ``to_dict``."""

        required = {
            "schema",
            "status",
            "candidate",
            "draft",
            "review",
            "drafts",
            "reviews",
            "automated_results",
            "release",
        }
        if not isinstance(payload, Mapping):
            raise WorkflowError("workflow snapshot must be an object")
        missing = required.difference(payload)
        unknown = set(payload).difference(required)
        if missing:
            raise WorkflowError(
                "workflow snapshot is missing fields: " + ", ".join(sorted(missing))
            )
        if unknown:
            raise WorkflowError(
                "workflow snapshot has unknown fields: " + ", ".join(sorted(unknown))
            )
        if payload["schema"] != "scirel.workflow-state.dev":
            raise WorkflowError(f"unsupported workflow snapshot schema: {payload['schema']}")

        candidate_payload = payload["candidate"]
        if not isinstance(candidate_payload, Mapping):
            raise WorkflowError("workflow snapshot candidate must be an object")
        try:
            candidate = CandidatePackage.from_mapping(candidate_payload)
        except ValueError as error:
            raise WorkflowError(f"invalid workflow snapshot candidate: {error}") from error
        workflow = cls(candidate)

        drafts = payload["drafts"]
        reviews = payload["reviews"]
        automated_results = payload["automated_results"]
        if not all(isinstance(value, list) for value in (drafts, reviews, automated_results)):
            raise WorkflowError("workflow snapshot histories must be arrays")

        def draft_from_mapping(value: Mapping[str, Any]) -> StandardizedDraft:
            return StandardizedDraft(
                draft_id=value.get("draft_id"),
                candidate_id=value.get("candidate_id"),
                assets=tuple(value.get("assets", ())),
                dependency_asset_ids=tuple(value.get("dependency_asset_ids", ())),
                evidence=tuple(value.get("evidence", ())),
                gaps=tuple(value.get("gaps", ())),
                status=value.get("status", WorkflowStatus.DRAFT.value),
            )

        def review_from_mapping(value: Mapping[str, Any]) -> ReviewDecision:
            return ReviewDecision(
                draft_id=value.get("draft_id"),
                outcome=value.get("outcome"),
                reviewer=value.get("reviewer"),
                notes=value.get("notes", ""),
            )

        try:
            workflow.record.drafts = [
                draft_from_mapping(value) for value in drafts
            ]
            workflow.record.reviews = [
                review_from_mapping(value) for value in reviews
            ]
            workflow.record.automated_results = [
                AutomatedCheckResult.from_mapping(value) for value in automated_results
            ]
            current_draft = payload["draft"]
            current_review = payload["review"]
            workflow.record.draft = (
                draft_from_mapping(current_draft)
                if current_draft is not None
                else None
            )
            workflow.record.review = (
                review_from_mapping(current_review)
                if current_review is not None
                else None
            )
            current_release = payload["release"]
            workflow.record.release = (
                ReleaseManifest.from_mapping(current_release)
                if current_release is not None
                else None
            )
        except (KeyError, TypeError, ValueError) as error:
            raise WorkflowError(f"invalid workflow snapshot: {error}") from error

        workflow._validate_restored_record()

        try:
            expected_status = WorkflowStatus(payload["status"])
        except ValueError as error:
            raise WorkflowError(f"invalid workflow snapshot status: {payload['status']}") from error
        if workflow.status is not expected_status:
            raise WorkflowError(
                "workflow snapshot status does not match its domain records"
            )
        return workflow

    def _validate_restored_record(self) -> None:
        """Validate relationships that individual record schemas cannot see."""

        record = self.record
        candidate = record.candidate
        result_ids: set[str] = set()
        for result in record.automated_results:
            if result.result_id in result_ids:
                raise WorkflowError(
                    "workflow snapshot has duplicate automated result_id"
                )
            result_ids.add(result.result_id)
            if result.candidate_id != candidate.candidate_id:
                raise WorkflowError(
                    "workflow snapshot automated result refers to another candidate"
                )
            if result.source_digest != candidate.source_digest:
                raise WorkflowError(
                    "workflow snapshot automated result source digest does not match"
                )

        drafts_by_id: dict[str, StandardizedDraft] = {}
        for draft in record.drafts:
            if draft.draft_id in drafts_by_id:
                raise WorkflowError("workflow snapshot has duplicate draft_id")
            if draft.candidate_id != candidate.candidate_id:
                raise WorkflowError(
                    "workflow snapshot draft refers to another candidate"
                )
            drafts_by_id[draft.draft_id] = draft
        if record.drafts and not candidate.automated_ready:
            raise WorkflowError(
                "workflow snapshot has drafts for a candidate that is not automated_ready"
            )
        if record.draft is not None:
            if record.draft.candidate_id != candidate.candidate_id:
                raise WorkflowError(
                    "workflow snapshot current draft refers to another candidate"
                )
            historical = drafts_by_id.get(record.draft.draft_id)
            if historical is None or historical.draft_digest != record.draft.draft_digest:
                raise WorkflowError(
                    "workflow snapshot current draft is not its latest history record"
                )
            latest_draft = record.drafts[-1]
            if (
                latest_draft.draft_id != record.draft.draft_id
                or latest_draft.draft_digest != record.draft.draft_digest
            ):
                raise WorkflowError(
                    "workflow snapshot current draft is not its latest history record"
                )
        elif record.drafts:
            raise WorkflowError("workflow snapshot has draft history without current draft")

        reviewed_drafts: set[str] = set()
        for review in record.reviews:
            if review.draft_id not in drafts_by_id:
                raise WorkflowError("workflow snapshot review refers to an unknown draft")
            if review.draft_id in reviewed_drafts:
                raise WorkflowError("workflow snapshot has duplicate review for a draft")
            reviewed_drafts.add(review.draft_id)
        if record.review is not None:
            if record.draft is None or record.review.draft_id != record.draft.draft_id:
                raise WorkflowError(
                    "workflow snapshot current review refers to another draft"
                )
            if (
                not record.reviews
                or record.reviews[-1].to_dict() != record.review.to_dict()
            ):
                raise WorkflowError(
                    "workflow snapshot current review is not its latest history record"
                )

        release = record.release
        if release is None:
            return
        if not candidate.automated_ready:
            raise WorkflowError(
                "workflow snapshot release candidate is not automated_ready"
            )
        if record.draft is None:
            raise WorkflowError("workflow snapshot release has no current draft")
        if record.draft.status is not WorkflowStatus.APPROVED:
            raise WorkflowError("workflow snapshot release draft is not approved")
        if (
            record.review is None
            or record.review.outcome is not ReviewOutcome.APPROVED
        ):
            raise WorkflowError("workflow snapshot release has no approved review")
        if release.candidate_id != candidate.candidate_id:
            raise WorkflowError("workflow snapshot release candidate_id does not match")
        if release.draft_id != record.draft.draft_id:
            raise WorkflowError("workflow snapshot release draft_id does not match")
        if release.candidate_digest != candidate.package_digest:
            raise WorkflowError("workflow snapshot release candidate digest does not match")
        if release.draft_digest != record.draft.draft_digest:
            raise WorkflowError("workflow snapshot release draft digest does not match")
        asset_ids = tuple(str(asset.get("asset_id", "")) for asset in record.draft.assets)
        if release.approved_assets != asset_ids:
            raise WorkflowError("workflow snapshot release asset set does not match draft")
        self._validate_release_versions(record.draft, release.release_version)

    @staticmethod
    def _validate_release_versions(
        draft: StandardizedDraft, release_version: str
    ) -> None:
        for index, asset in enumerate(draft.assets):
            version = asset.get("version")
            implementation_version = (
                version.get("implementation_version")
                if isinstance(version, Mapping)
                else None
            )
            if implementation_version != release_version:
                asset_id = asset.get("asset_id") or f"asset[{index}]"
                raise WorkflowError(
                    "draft asset implementation_version does not match release_version: "
                    + str(asset_id)
                )

    def create_draft(
        self,
        *,
        draft_id: str,
        assets: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
        dependency_asset_ids: list[str] | tuple[str, ...] = (),
        evidence: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        gaps: list[str] | tuple[str, ...] = (),
    ) -> StandardizedDraft:
        if self.record.release is not None:
            raise WorkflowError("released workflow cannot create another draft")
        if self.record.draft is not None and self.record.review is None:
            raise WorkflowError("current draft must be reviewed before rework")
        if self.record.review is not None and self.record.review.outcome not in (
            ReviewOutcome.NEEDS_EVIDENCE,
            ReviewOutcome.REWORK_REQUESTED,
        ):
            raise WorkflowError("only evidence or rework decisions can create a new draft")
        if not self.record.candidate.automated_ready:
            raise WorkflowError("candidate automated checks are not ready")
        draft = StandardizedDraft(
            draft_id=draft_id,
            candidate_id=self.record.candidate.candidate_id,
            assets=tuple(dict(asset) for asset in assets),
            dependency_asset_ids=tuple(dependency_asset_ids),
            evidence=tuple(dict(item) for item in evidence),
            gaps=tuple(gaps),
        )
        self.record.draft = draft
        self.record.drafts.append(draft)
        self.record.review = None
        return draft

    def update_open_draft(
        self,
        *,
        assets: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
        dependency_asset_ids: list[str] | tuple[str, ...] = (),
        evidence: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        gaps: list[str] | tuple[str, ...] = (),
    ) -> StandardizedDraft:
        """Replace an unsubmitted draft while preserving its review identity."""

        current = self._require_draft()
        if self.status not in (
            WorkflowStatus.DRAFT,
            WorkflowStatus.REVIEW_PENDING,
        ):
            raise WorkflowError("only an open draft can be updated")
        if (
            not self.record.drafts
            or self.record.drafts[-1].draft_id != current.draft_id
        ):
            raise WorkflowError("current draft is not its latest history record")

        updated = StandardizedDraft(
            draft_id=current.draft_id,
            candidate_id=current.candidate_id,
            assets=tuple(dict(asset) for asset in assets),
            dependency_asset_ids=tuple(dependency_asset_ids),
            evidence=tuple(dict(item) for item in evidence),
            gaps=tuple(gaps),
            status=current.status,
        )
        self.record.draft = updated
        self.record.drafts[-1] = updated
        return updated

    def apply_automated_result(self, result: AutomatedCheckResult) -> CandidatePackage:
        """Apply a host check result before expert-review preparation."""

        for existing in self.record.automated_results:
            if existing.result_id != result.result_id:
                continue
            if existing.result_digest != result.result_digest:
                raise WorkflowError(
                    "automated result_id was reused with different content"
                )
            return self.record.candidate
        if self.record.draft is not None or self.record.release is not None:
            raise WorkflowError("automated results cannot change a drafted workflow")
        try:
            candidate = self.record.candidate.apply_automated_result(result)
        except ValueError as error:
            raise WorkflowError(str(error)) from error
        self.record.candidate = candidate
        self.record.automated_results.append(result)
        return candidate

    def submit_for_review(self) -> StandardizedDraft:
        draft = self._require_draft()
        if self.status is not WorkflowStatus.DRAFT:
            raise WorkflowError(f"draft cannot enter review from {self.status.value}")
        draft.status = WorkflowStatus.REVIEW_PENDING
        return draft

    def start_review(self) -> StandardizedDraft:
        """Freeze the queued draft immediately before an expert sees it."""

        draft = self._require_draft()
        if self.status is not WorkflowStatus.REVIEW_PENDING:
            raise WorkflowError("only a queued draft can start expert review")
        draft.status = WorkflowStatus.REVIEW_IN_PROGRESS
        self.record.drafts[-1] = draft
        return draft

    def record_review(self, decision: ReviewDecision) -> ReviewDecision:
        draft = self._require_draft()
        if self.status is not WorkflowStatus.REVIEW_IN_PROGRESS:
            raise WorkflowError(
                "a draft must be review_in_progress before a review decision"
            )
        if decision.draft_id != draft.draft_id:
            raise WorkflowError("review decision refers to a different draft")
        if decision.outcome is ReviewOutcome.APPROVED and draft.gaps:
            raise WorkflowError("a draft with unresolved gaps cannot be approved")
        self.record.review = decision
        self.record.reviews.append(decision)
        draft.status = {
            ReviewOutcome.APPROVED: WorkflowStatus.APPROVED,
            ReviewOutcome.NEEDS_EVIDENCE: WorkflowStatus.NEEDS_EVIDENCE,
            ReviewOutcome.REWORK_REQUESTED: WorkflowStatus.REWORK_REQUESTED,
            ReviewOutcome.REJECTED: WorkflowStatus.REJECTED,
        }[decision.outcome]
        self.record.drafts[-1] = draft
        return decision

    def release(
        self,
        *,
        release_id: str,
        catalog_ref: str,
        catalog_digest: str,
        wheel_ref: str,
        wheel_digest: str,
        release_version: str = "0.1.0.dev5",
    ) -> ReleaseManifest:
        draft = self._require_draft()
        if self.status is not WorkflowStatus.APPROVED:
            raise WorkflowError("only an approved draft can be released")
        if draft.gaps:
            raise WorkflowError("draft has unresolved gaps")
        if not draft.assets:
            raise WorkflowError("draft has no assets")
        approved_assets = tuple(
            str(asset["asset_id"])
            for asset in draft.assets
            if isinstance(asset, Mapping) and asset.get("asset_id")
        )
        if len(approved_assets) != len(draft.assets):
            raise WorkflowError("every draft asset must have an asset_id")
        self._validate_release_versions(draft, release_version)
        release = ReleaseManifest(
            release_id=release_id,
            draft_id=draft.draft_id,
            approved_assets=approved_assets,
            catalog_ref=catalog_ref,
            catalog_digest=catalog_digest,
            wheel_ref=wheel_ref,
            wheel_digest=wheel_digest,
            candidate_id=self.record.candidate.candidate_id,
            candidate_digest=self.record.candidate.package_digest,
            draft_digest=draft.draft_digest,
            release_version=release_version,
        )
        self.record.release = release
        return release

    def _require_draft(self) -> StandardizedDraft:
        if self.record.draft is None:
            raise WorkflowError("workflow has no standardized draft")
        return self.record.draft
