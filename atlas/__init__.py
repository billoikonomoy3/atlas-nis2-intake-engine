"""Atlas — NIS2 readiness engine.

A deterministic Stage-3 -> compliance-baseline engine with a cited, model-assisted
document-extraction slice for control RM-21D-01. The law is determined by pure
deterministic code (one source of truth, the ruleset YAML + engine package); models
appear ONLY in document extraction, never in the judgment path.
"""

from __future__ import annotations

ENGINE_VERSION = "2.0.0"

__all__ = ["ENGINE_VERSION"]
