import pathlib
import time
from typing import TYPE_CHECKING

import pytest

from core.manifest import ManifestRepository
from core.models.book import BookStatus
from core.models.manifest import BookManifest

if TYPE_CHECKING:
    from pathlib import Path


def make_manifest() -> BookManifest:
    return BookManifest(source_file="book.pdf", slug="book")


def test_exists_reflects_file_presence(tmp_path: Path) -> None:
    repo = ManifestRepository(tmp_path / "manifest.json")
    assert repo.exists() is False
    repo.save(make_manifest())
    assert repo.exists() is True


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    repo = ManifestRepository(tmp_path / "manifest.json")
    manifest = make_manifest()
    repo.save(manifest)
    loaded = repo.load()
    assert loaded.source_file == "book.pdf"
    assert loaded.slug == "book"
    assert loaded.status is BookStatus.PENDING


def test_save_creates_missing_parent_directories(tmp_path: Path) -> None:
    repo = ManifestRepository(tmp_path / "nested" / "deep" / "manifest.json")
    repo.save(make_manifest())
    assert repo.exists()


def test_save_serializes_camel_case_aliases(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    ManifestRepository(path).save(make_manifest())
    content = path.read_text(encoding="utf-8")
    assert '"sourceFile"' in content
    assert '"source_file"' not in content


def test_save_removes_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    ManifestRepository(path).save(make_manifest())
    assert not path.with_name("manifest.json.tmp").exists()


def test_save_retries_replace_on_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "manifest.json"
    repo = ManifestRepository(path)
    calls = {"n": 0}
    real_replace = pathlib.Path.replace

    def flaky(self: pathlib.Path, target: pathlib.Path) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError
        real_replace(self, target)

    sleeps: list[float] = []
    monkeypatch.setattr(pathlib.Path, "replace", flaky)
    monkeypatch.setattr(time, "sleep", lambda seconds: sleeps.append(seconds))

    repo.save(make_manifest())

    assert calls["n"] == 3
    assert repo.exists()
    assert sleeps == [ManifestRepository.REPLACE_BACKOFF] * 2


def test_save_raises_after_exhausting_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = ManifestRepository(tmp_path / "manifest.json")
    calls = {"n": 0}

    def always_fail(self: pathlib.Path, target: pathlib.Path) -> None:
        calls["n"] += 1
        raise PermissionError

    monkeypatch.setattr(pathlib.Path, "replace", always_fail)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    with pytest.raises(PermissionError):
        repo.save(make_manifest())

    assert calls["n"] == ManifestRepository.REPLACE_RETRIES
