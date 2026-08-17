"""Shared Pydantic models.

This package is the contract between pipeline stages.
Nothing in `domain` imports from another ReefCommand package, which keeps the
dependency direction one way and the stages independently testable.
"""
