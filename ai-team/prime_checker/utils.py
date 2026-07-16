import math


def validate_input(number: int) -> str | None:
    """Return an error message if input is invalid, else None."""
    if not isinstance(number, int) or isinstance(number, bool):
        return f"{number!r} is not an integer."
    return None


def find_first_divisor(number: int) -> int | None:
    """Return the smallest divisor > 1 (other than number), or None if prime."""
    if number % 2 == 0:
        return 2
    for i in range(3, int(math.isqrt(number)) + 1, 2):
        if number % i == 0:
            return i
    return None
