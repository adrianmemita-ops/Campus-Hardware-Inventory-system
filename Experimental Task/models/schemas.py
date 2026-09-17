from pydantic import BaseModel, Field, field_validator, EmailStr
import re


class UserRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]+", value):
            raise ValueError("Username must be alphanumeric and may include underscores")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[@#$%^&*!]", value):
            raise ValueError("Password must contain at least one special character (@#$%^&*!)")
        return value


class InventorySchema(BaseModel):
    item_name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    quantity: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Quantity must be non-negative")
        return value

    @field_validator("unit_price")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Unit price must be non-negative")
        return value


class BorrowSchema(BaseModel):
    quantity: int = Field(default=1, ge=1)
    student_name: str = Field(..., min_length=2, max_length=100)
    student_id: str = Field(..., min_length=2, max_length=30)
    section: str = Field(..., min_length=1, max_length=50)
    course: str = Field(..., min_length=2, max_length=100)
    status: str = Field(default="Borrowed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"Borrowed", "Missing"}:
            raise ValueError("Status must be Borrowed or Missing")
        return value


class ReservationSchema(BaseModel):
    quantity: int = Field(default=1, ge=1)
    student_name: str = Field(..., min_length=2, max_length=100)
    student_id: str = Field(..., min_length=2, max_length=30)
    section: str = Field(..., min_length=1, max_length=50)
    course: str = Field(..., min_length=2, max_length=100)
    reservation_date: str = Field(..., min_length=8, max_length=20)
    reservation_time: str = Field(..., min_length=3, max_length=10)

