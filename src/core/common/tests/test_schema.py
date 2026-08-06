from typing import final

from core.common.schema import CamelCaseModel


@final
class Sample(CamelCaseModel):
    first_name: str
    item_count: int


def test_accepts_camel_case_alias() -> None:
    model = Sample.model_validate({"firstName": "Ada", "itemCount": 3})
    assert model.first_name == "Ada"
    assert model.item_count == 3


def test_accepts_snake_case_field_name() -> None:
    model = Sample.model_validate({"first_name": "Ada", "item_count": 3})
    assert model.first_name == "Ada"


def test_serializes_to_camel_case() -> None:
    dumped = Sample(first_name="Ada", item_count=3).model_dump(by_alias=True)
    assert dumped == {"firstName": "Ada", "itemCount": 3}


def test_reads_from_attributes() -> None:
    class Source:
        first_name = "Ada"
        item_count = 3

    model = Sample.model_validate(Source())
    assert model.first_name == "Ada"
    assert model.item_count == 3
