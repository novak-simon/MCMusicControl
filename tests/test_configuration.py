import json

import pytest

from configuration import load_config
from keyboard_controller import ControlMode


def test_loads_default_configuration() -> None:
    config = load_config(__import__("pathlib").Path("config.json"))
    assert config.mappings[("D", 4)].key == "space"
    assert config.mappings[("D", 4)].mode is ControlMode.SUSTAINED
    assert config.mappings[("E", 5)].key == "escape"
    assert config.trigger_hold_seconds == 0.06
    assert config.mouse_sensitivity == 10


def test_rejects_invalid_mode(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mappings": {"A4": {"key": "w", "mode": "bad"}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid mode"):
        load_config(path)


def test_mouse_sensitivity_defaults_for_older_configuration(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "release_delay_seconds": 0.08,
                "trigger_hold_seconds": 0.06,
                "mappings": {"A4": {"key": "mouse_move_right", "mode": "sustained"}},
            }
        ),
        encoding="utf-8",
    )
    assert load_config(path).mouse_sensitivity == 10


def test_rejects_non_positive_mouse_sensitivity(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "mouse_sensitivity": 0,
                "release_delay_seconds": 0.08,
                "trigger_hold_seconds": 0.06,
                "mappings": {"A4": {"key": "mouse_move_right", "mode": "sustained"}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mouse_sensitivity must be positive"):
        load_config(path)
