import pytest

from core.models.stage import FromStage, Stage


def test_stage_order() -> None:
    assert list(Stage) == [
        Stage.EXTRACT,
        Stage.CHAPTERS,
        Stage.CHUNK,
        Stage.TTS,
        Stage.MERGE,
    ]
    assert Stage.EXTRACT < Stage.MERGE


def test_banner_includes_position_and_title() -> None:
    assert Stage.EXTRACT.banner == "Stage 1/5: Extract text"
    assert Stage.MERGE.banner == "Stage 5/5: Merge MP3 files"


@pytest.mark.parametrize(
    ("from_stage", "stage"),
    [
        (FromStage.EXTRACT, Stage.EXTRACT),
        (FromStage.CHAPTERS, Stage.CHAPTERS),
        (FromStage.CHUNK, Stage.CHUNK),
        (FromStage.TTS, Stage.TTS),
        (FromStage.MERGE, Stage.MERGE),
    ],
)
def test_from_stage_maps_to_ordered_stage(
    from_stage: FromStage, stage: Stage
) -> None:
    assert from_stage.stage is stage


def test_from_stage_cli_values() -> None:
    assert FromStage.EXTRACT.value == "extract"
    assert FromStage("merge") is FromStage.MERGE
