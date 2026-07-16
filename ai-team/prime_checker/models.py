from dataclasses import dataclass


@dataclass
class PrimeResult:
    number: int
    is_prime: bool
    explanation: str
