"""Nested-model validation example.

Run with:  python examples/nested.py
"""

from __future__ import annotations

from typing import Optional

from validix import BaseModel, Field, ValidationError


class Address(BaseModel):
    street: str
    city: str
    zip: str = Field(pattern=r"^\d{4,10}$")


class Order(BaseModel):
    id: int
    item: str
    qty: int = Field(gt=0)


class Customer(BaseModel):
    name: str
    address: Address
    secondary_addresses: list[Address] = []
    last_order: Optional[Order] = None


def main() -> None:
    payload = {
        "name": "Ada",
        "address": {"street": "1 Babbage Way", "city": "London", "zip": "EC1A"},
        "secondary_addresses": [
            {"street": "2 Turing Pl", "city": "Manchester", "zip": "M11"},
        ],
        "last_order": {"id": 99, "item": "book", "qty": 2},
    }
    customer = Customer(**payload)
    print(customer.model_dump_json(indent=2))

    print("\n--- one of the nested addresses is bad -----------------")
    try:
        Customer(
            name="Ada",
            address={"street": "1", "city": "London", "zip": "ABC"},
            secondary_addresses=[
                {"street": "2", "city": "Manchester"},  # missing zip
            ],
        )
    except ValidationError as exc:
        for err in exc.errors():
            print(f"  {'.'.join(map(str, err['loc']))}: {err['msg']}  [{err['type']}]")


if __name__ == "__main__":
    main()
