from focus_guard import minecraft_is_focused


def test_focus_guard_is_callable() -> None:
    assert isinstance(minecraft_is_focused(), bool)
