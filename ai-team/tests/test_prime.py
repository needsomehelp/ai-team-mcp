import pytest
from prime_checker import check_prime


@pytest.mark.parametrize("n", [2, 3, 5, 7, 11, 13, 97, 7919])
def test_primes(n):
    result = check_prime(n)
    assert result.is_prime is True
    assert result.number == n


@pytest.mark.parametrize("n", [0, 1, 4, 6, 9, 15, 100, 7920])
def test_non_primes(n):
    result = check_prime(n)
    assert result.is_prime is False
    assert result.number == n


def test_negative():
    result = check_prime(-5)
    assert result.is_prime is False


def test_explanation_includes_divisor():
    result = check_prime(15)
    assert "3" in result.explanation
    assert "5" in result.explanation


def test_invalid_type():
    with pytest.raises(TypeError):
        check_prime(3.14)

    with pytest.raises(TypeError):
        check_prime(True)
