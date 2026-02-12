from typing import TypeVar

T = TypeVar("T")


def assert_and_get_one(items: list[T]) -> T:
    assert len(items) == 1
    return items[0]
