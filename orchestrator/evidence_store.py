"""Evidence Store: In-memory storage and management of collected evidence."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from models.evidence import Evidence, EvidenceType


class EvidenceStore:
    """Manages all evidence collected during an incident investigation.

    Features:
    - Stores Evidence objects with auto-ID assignment
    - Prevents duplicate evidence
    - Supports lookup by id, source, service, type
    - Merges similar evidence and boosts confidence
    - Preserves insertion order
    """

    def __init__(self) -> None:
        """Initialize an empty evidence store."""
        self._evidence_by_id: dict[str, Evidence] = {}
        self._seen_hashes: set[str] = set()
        self._insertion_order: list[str] = []

    def _hash_evidence(self, evidence: Evidence) -> str:
        """Compute a content hash to detect duplicates.

        Two pieces of evidence are considered duplicates if they have the same:
        - source
        - type
        - service (if applicable)
        - description
        """
        content = json.dumps(
            {
                "source": evidence.source,
                "type": evidence.type,
                "service": evidence.source,
                "description": evidence.description,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def add_evidence(self, evidence: Evidence, deduplicate: bool = True) -> str:
        """Add a piece of evidence to the store.

        Args:
            evidence: The Evidence object to add.
            deduplicate: If True, attempt to merge with existing similar evidence.

        Returns:
            The ID of the evidence (newly assigned or existing if deduplicated).
        """
        if not evidence.type:
            raise ValueError("Evidence must have a type.")

        content_hash = self._hash_evidence(evidence)

        if deduplicate and content_hash in self._seen_hashes:
            existing_id = next(
                (eid for eid, e in self._evidence_by_id.items() if self._hash_evidence(e) == content_hash),
                None,
            )
            if existing_id:
                return self._boost_confidence(existing_id)

        if not evidence.__dict__.get("id"):
            evidence_copy = evidence.model_copy(update={"id": str(uuid.uuid4())})
        else:
            evidence_copy = evidence

        evidence_id = str(evidence_copy.__dict__.get("id") or str(uuid.uuid4()))

        self._evidence_by_id[evidence_id] = evidence_copy
        self._seen_hashes.add(content_hash)
        self._insertion_order.append(evidence_id)

        return evidence_id

    def _boost_confidence(self, evidence_id: str, boost: float = 0.05) -> str:
        """Slightly increase confidence when duplicate evidence is found.

        Args:
            evidence_id: The ID of the existing evidence.
            boost: The amount to increase confidence (capped at 1.0).

        Returns:
            The evidence ID.
        """
        evidence = self._evidence_by_id[evidence_id]
        new_confidence = min(1.0, evidence.relevance + boost)
        self._evidence_by_id[evidence_id] = evidence.model_copy(
            update={"relevance": new_confidence}
        )
        return evidence_id

    def get_by_id(self, evidence_id: str) -> Evidence | None:
        """Retrieve evidence by ID."""
        return self._evidence_by_id.get(evidence_id)

    def get_by_source(self, source: str) -> list[Evidence]:
        """Retrieve all evidence from a specific source."""
        return [e for e in self._evidence_by_id.values() if e.source.lower() == source.lower()]

    def get_by_service(self, service: str) -> list[Evidence]:
        """Retrieve all evidence related to a specific service."""
        results = []
        for evidence in self._evidence_by_id.values():
            if service.lower() in evidence.source.lower():
                results.append(evidence)
        return results

    def get_by_type(self, evidence_type: EvidenceType | str) -> list[Evidence]:
        """Retrieve all evidence of a specific type."""
        if isinstance(evidence_type, str):
            try:
                evidence_type = EvidenceType(evidence_type)
            except ValueError:
                return []

        return [e for e in self._evidence_by_id.values() if e.type == evidence_type]

    def get_sorted_by_confidence(self, reverse: bool = True) -> list[Evidence]:
        """Get all evidence sorted by relevance/confidence score.

        Args:
            reverse: If True, sort highest confidence first.

        Returns:
            List of Evidence objects sorted by relevance.
        """
        sorted_evidence = sorted(
            self._evidence_by_id.values(),
            key=lambda e: e.relevance,
            reverse=reverse,
        )
        return sorted_evidence

    def get_all(self) -> list[Evidence]:
        """Get all evidence in insertion order."""
        return [self._evidence_by_id[eid] for eid in self._insertion_order]

    def count(self) -> int:
        """Return the total number of evidence items."""
        return len(self._evidence_by_id)

    def export_to_json(self) -> str:
        """Export all evidence to a JSON string.

        Returns:
            JSON string representation of all evidence in insertion order.
        """
        evidence_list = self.get_all()
        evidence_dicts = [e.model_dump(mode="json") for e in evidence_list]
        return json.dumps(evidence_dicts, indent=2, sort_keys=False)

    def export_to_dict(self) -> list[dict[str, Any]]:
        """Export all evidence to a list of dictionaries."""
        evidence_list = self.get_all()
        return [e.model_dump(mode="json") for e in evidence_list]

    def clear(self) -> None:
        """Clear all evidence from the store."""
        self._evidence_by_id.clear()
        self._seen_hashes.clear()
        self._insertion_order.clear()

    def merge_from(self, other: EvidenceStore) -> None:
        """Merge evidence from another EvidenceStore into this one.

        Args:
            other: Another EvidenceStore to merge from.
        """
        for evidence in other.get_all():
            self.add_evidence(evidence, deduplicate=True)
