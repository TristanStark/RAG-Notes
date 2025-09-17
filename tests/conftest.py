import pytest


@pytest.fixture(autouse=True)
def env_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGES_FOLDER", str(tmp_path / "images"))
    monkeypatch.setenv("POLL_INTERVAL", "1")
    monkeypatch.setenv("MAX_RETRIES", "1")
    yield
