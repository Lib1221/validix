"""Validate JSON request payloads coming from a tiny HTTP API.

Run with:  python examples/api_validation.py
"""

from __future__ import annotations

import json
from typing import Literal

from validix import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class CreateAccountRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str
    role: Literal["user", "admin", "guest"] = "user"
    age: int = Field(ge=13, lt=130)

    @field_validator("username")
    def _ban_reserved(cls, v: str) -> str:
        if v in {"admin", "root", "system"}:
            raise ValueError(f"username {v!r} is reserved")
        return v

    @model_validator(mode="after")
    def _passwords_match(self):  # type: ignore[no-untyped-def]
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self


def handle_request(body: str) -> dict:
    try:
        req = CreateAccountRequest.model_validate_json(body)
    except ValidationError as exc:
        return {"status": 422, "errors": exc.errors()}
    return {"status": 201, "username": req.username, "role": req.role}


SAMPLES = [
    json.dumps(
        {
            "username": "ada",
            "password": "supersecret1",
            "password_confirm": "supersecret1",
            "age": 37,
        }
    ),
    json.dumps(
        {
            "username": "x!",
            "password": "short",
            "password_confirm": "different",
            "age": 5,
        }
    ),
    json.dumps(
        {
            "username": "admin",
            "password": "supersecret1",
            "password_confirm": "supersecret1",
            "age": 99,
        }
    ),
    "{not json",
]


def main() -> None:
    for i, body in enumerate(SAMPLES, 1):
        print(f"--- request {i} -----------------------------------------")
        print(body)
        print("→", json.dumps(handle_request(body), indent=2))
        print()


if __name__ == "__main__":
    main()
