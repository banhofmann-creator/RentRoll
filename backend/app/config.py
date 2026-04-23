from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rentroll"
    postgres_user: str = "rentroll"
    postgres_password: str = "rentroll"

    upload_dir: str = "./uploads"
    session_secret: str = "change-me-to-a-random-string"
    anthropic_api_key: str = ""

    database_url: str | None = None

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
