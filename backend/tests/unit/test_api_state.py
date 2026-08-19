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
        replan_trigger: str | None = None,
    ) -> object:
        received.update(
            scenario_id=scenario_id,
            site_ids=site_ids,
            offline=offline,
            replan_trigger=replan_trigger,
        )
        return sentinel

    monkeypatch.setattr(state, "_baseline_plan", None)
    monkeypatch.setattr(state, "_current_plan", None)
    monkeypatch.setattr(state, "run", capture_run)

    assert state.current_plan() is sentinel
    assert received == {
        "scenario_id": state.DEFAULT_SCENARIO_ID,
        "site_ids": state.DEFAULT_SITE_IDS,
        "offline": True,
        "replan_trigger": "demo_baseline",
    }


def test_single_site_recompute_is_retained_without_publishing(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(state, "_latest_site_plans", {})
    monkeypatch.setattr(state, "run", lambda *args, **kwargs: sentinel)

    result = state.recompute(
        state.DEFAULT_SCENARIO_ID,
        ["cheeca_rocks"],
        offline=False,
        publish=False,
    )

    assert result is sentinel
    assert state.latest_site_plan("cheeca_rocks") is sentinel
