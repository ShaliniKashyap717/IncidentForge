"""Repository search helpers."""

from __future__ import annotations

from typing import Any


def search_text_fields(
	records: list[dict[str, Any]],
	fields: list[str],
	query: str,
) -> list[dict[str, Any]]:
	"""Search plain-text fields across a list of metadata records."""

	lowered = query.lower().strip()
	if not lowered:
		return records

	matches: list[dict[str, Any]] = []
	for record in records:
		corpus = " ".join(str(record.get(field, "")) for field in fields).lower()
		if lowered in corpus:
			matches.append(record)
	return matches


def search_any_keyword(
	records: list[dict[str, Any]],
	fields: list[str],
	keywords: list[str],
) -> list[dict[str, Any]]:
	"""Return records that match at least one keyword in the target fields."""

	lowered_keywords = [keyword.lower() for keyword in keywords if keyword.strip()]
	if not lowered_keywords:
		return records

	results: list[dict[str, Any]] = []
	for record in records:
		corpus = " ".join(str(record.get(field, "")) for field in fields).lower()
		if any(keyword in corpus for keyword in lowered_keywords):
			results.append(record)
	return results
