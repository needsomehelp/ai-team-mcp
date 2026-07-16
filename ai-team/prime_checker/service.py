from .models import PrimeResult
from .utils import validate_input, find_first_divisor


def check_prime(number: int) -> PrimeResult:
    """Check whether a number is prime and return the result with explanation."""
    error = validate_input(number)
    if error:
        raise TypeError(error)

    if number <= 1:
        return PrimeResult(
            number=number,
            is_prime=False,
            explanation=f"{number} is not prime because prime numbers must be greater than 1.",
        )

    if number == 2:
        return PrimeResult(
            number=number,
            is_prime=True,
            explanation="2 is prime. It is the only even prime number.",
        )

    divisor = find_first_divisor(number)
    if divisor is not None:
        return PrimeResult(
            number=number,
            is_prime=False,
            explanation=f"{number} is not prime because it is divisible by {divisor} ({number} = {divisor} x {number // divisor}).",
        )

    return PrimeResult(
        number=number,
        is_prime=True,
        explanation=f"{number} is prime. It has no divisors other than 1 and itself.",
    )
