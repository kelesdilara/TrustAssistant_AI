from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str

    database_url: str
    docker_database_url: str

    redis_url: str
    docker_redis_url: str

    ollama_base_url: str
    docker_ollama_base_url: str
    ollama_model: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    backend_port: int
    postgres_port: int
    redis_port: int
    ollama_port: int

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()