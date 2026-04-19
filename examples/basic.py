"""Basic usage of validix.

Run with:  python examples/basic.py
"""

from __future__ import annotations

from validix import BaseModel, Field, ValidationError


class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=64)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    is_active: bool = True


def main() -> None:
    print("--- valid input -----------------------------------------")
    user = User(id="42", name="Ada Lovelace", email="ada@example.com")
    print(user)
    print(user.model_dump_json(indent=2))

    print("\n--- invalid input ---------------------------------------")
    try:
        User(id="not-a-number", name="", email="not-an-email")
    except ValidationError as exc:
        print(exc)
        print()
        print(f"raised {exc.error_count()} errors as JSON:")
        print(exc.json(indent=2))


if __name__ == "__main__":
    main()
