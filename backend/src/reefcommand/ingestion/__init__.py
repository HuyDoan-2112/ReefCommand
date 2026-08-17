"""External data adapters.

Every adapter returns values tagged with their provenance and never raises past
its own boundary during a demo: a live call is wrapped with a short timeout and
falls back to the cached copy.
"""
