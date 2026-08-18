"""Unit checks for the API's in-process plan state."""

from reefcommand.api import state


def test_current_plan_creates_an_explicit_offline_baseline(monkeypatch) -> None:
    sentinel = object()
    received: dict[str, object] = {}

    def capture_run(
        scenario_id: str,
        site_ids: list[str],
        *,
        offline: bool | None = None,
    ) -> object:
        received.update(
            scenario_id=scenario_id,
            site_ids=site_ids,
            offline=offline,
        )
        return sentinel

    monkeypatch.setattr(state, "_current_plan", None)
    monkeypatch.setattr(state, "run", capture_run)

    assert state.current_plan() is sentinel
    assert received == {
        "scenario_id": state.DEFAULT_SCENARIO_ID,
        "site_ids": state.DEFAULT_SITE_IDS,
        "offline": True,
    }
