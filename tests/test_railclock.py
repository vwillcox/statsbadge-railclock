"""Checks run by statsbadge's extension workflow: `python tests/test_railclock.py`."""

import ast
import os

from statsbadge import badge_api

from statsbadge_railclock import RailClock


def test_sends_the_host_time():
    frame = {}
    RailClock({}).sample(frame, 1.0)
    clock = frame["railclock"]
    assert 0 <= clock["hour"] < 24
    assert 0 <= clock["minute"] < 60
    assert 0 <= clock["seconds"] < 62


def test_ships_what_the_badge_needs():
    assert RailClock.available()
    for path in (RailClock.badge_module, *RailClock.badge_assets):
        assert os.path.isfile(path), path
        assert os.path.getsize(path) > 0, path


def test_badge_module_keeps_to_the_badge_api():
    """Only what statsbadge publishes for badge modules, at its current version."""
    source = open(RailClock.badge_module, encoding="utf-8").read()
    assert f"api={badge_api.VERSION}" in source
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        if node.value.id in badge_api.NAMES:
            assert node.attr in badge_api.NAMES[node.value.id], (
                f"{node.value.id}.{node.attr} is not in badge_api")
    imported = {alias.name for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Import) for alias in node.names}
    app_modules = {"deck", "app", "net", "splash", "setup"}
    assert not imported & app_modules, imported & app_modules


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
