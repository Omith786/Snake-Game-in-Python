import json

import pytest

from snake.highscore import ENV_VAR, HighScoreStore, default_path, score_key


def test_missing_file_starts_empty(tmp_path):
    store = HighScoreStore(tmp_path / "scores.json")
    assert store.get("normal-walls") == 0
    assert store.as_dict() == {}


def test_submit_persists_only_improvements(tmp_path):
    path = tmp_path / "nested" / "scores.json"
    store = HighScoreStore(path)
    assert store.submit("normal-walls", 50)
    assert not store.submit("normal-walls", 50)
    assert not store.submit("normal-walls", 10)
    assert store.submit("normal-walls", 70)

    reloaded = HighScoreStore(path)
    assert reloaded.get("normal-walls") == 70
    assert json.loads(path.read_text()) == {"normal-walls": 70}


def test_zero_score_is_not_a_record(tmp_path):
    path = tmp_path / "scores.json"
    assert not HighScoreStore(path).submit("easy-wrap", 0)
    assert not path.exists()


@pytest.mark.parametrize("content", ["not json", "[1, 2]", '{"a": "high"}', '{"a": -5, "b": true}'])
def test_corrupt_or_invalid_files_are_ignored(tmp_path, content):
    path = tmp_path / "scores.json"
    path.write_text(content)
    store = HighScoreStore(path)
    assert store.as_dict() == {}
    assert store.submit("a", 5)
    assert HighScoreStore(path).get("a") == 5


def test_valid_entries_survive_alongside_invalid_ones(tmp_path):
    path = tmp_path / "scores.json"
    path.write_text('{"good": 30, "bad": "x"}')
    assert HighScoreStore(path).as_dict() == {"good": 30}


def test_unwritable_location_does_not_crash(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    # Parent "directory" is actually a file, so mkdir and write both fail.
    store = HighScoreStore(blocker / "scores.json")
    assert store.submit("k", 10)
    assert store.get("k") == 10


def test_default_path_respects_env(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "custom.json"))
    assert default_path() == tmp_path / "custom.json"
    monkeypatch.delenv(ENV_VAR)
    assert default_path().name == ".snake_highscores.json"


def test_score_key_separates_modes():
    assert score_key("Normal", False) == "normal-walls"
    assert score_key("Hard", True) == "hard-wrap"
