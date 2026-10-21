"""Tests des commandes de consultation."""

from pathlib import Path

import pytest

from festival.cli.commands import main


def test_summary(
    festival_data_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main([], default_data_path=festival_data_path)
    output = capsys.readouterr()

    assert result == 0
    assert "Deauville Festival du Rire 2027" in output.out
    assert "23 représentations" in output.out


def test_programme_includes_after_midnight_show(
    festival_data_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        ["programme", "--day", "2027-06-11"],
        default_data_path=festival_data_path,
    )
    output = capsys.readouterr()

    assert result == 0
    assert "After Hours" in output.out
    assert "12/06 01:00" in output.out


def test_artists_command(
    festival_data_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        ["artists"],
        default_data_path=festival_data_path,
    )
    output = capsys.readouterr()

    assert result == 0
    assert "Nora Lebrun : 4 représentation(s)" in output.out


def test_now_command(
    festival_data_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        ["now", "--at", "2027-06-11T21:00"],
        default_data_path=festival_data_path,
    )
    output = capsys.readouterr()

    assert result == 0
    assert "SUR SCÈNE" in output.out
    assert "Tall Tales" in output.out
    assert "À SUIVRE" in output.out


def test_missing_data_returns_readable_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        [],
        default_data_path=tmp_path / "missing.json",
    )
    output = capsys.readouterr()

    assert result == 1
    assert "Impossible de lire" in output.err
    assert "Traceback" not in output.err
