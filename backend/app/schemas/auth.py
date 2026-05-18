from pydantic import BaseModel, Field, field_validator


class _EmailPasswordModel(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = str(value or "").strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Gecerli bir e-posta adresi girilmelidir.")
        return cleaned


class RegisterRequest(_EmailPasswordModel):
    password: str = Field(min_length=6)


class LoginRequest(_EmailPasswordModel):
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
