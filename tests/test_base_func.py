import pytest


@pytest.fixture
def bebra():
    print('meow')


def test_simple():
    assert 1 == 1
