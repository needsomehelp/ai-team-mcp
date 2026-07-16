from prime_checker import check_prime


def main():
    try:
        raw = input("Enter a number: ")
        number = int(raw)
    except ValueError:
        print(f"'{raw}' is not a valid integer.")
        return

    result = check_prime(number)
    print(f"\nResult: {'PRIME' if result.is_prime else 'NOT PRIME'}")
    print(f"Explanation: {result.explanation}")


if __name__ == "__main__":
    main()
