"""Environment configuration for IncidentForge."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
	"""Centralized Gemini model configuration for IncidentForge."""

	model_name: str = os.getenv("INCIDENTFORGE_GEMINI_MODEL", "gemini-3.6-flash")
	api_key: str | None = os.getenv("GOOGLE_API_KEY")


SETTINGS = GeminiConfig()


def get_gemini_model_name() -> str:
	"""Return the configured Gemini model name."""

	return SETTINGS.model_name


def has_google_api_key() -> bool:
	"""Return whether a Gemini API key is available."""

	return SETTINGS.api_key is not None
