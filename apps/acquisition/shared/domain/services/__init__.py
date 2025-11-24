"""Servicios de dominio compartidos."""

from apps.acquisition.shared.domain.services.metadata_matcher import (
    MetadataMatcher,
    MatchResult,
)

__all__ = ["MetadataMatcher", "MatchResult"]
