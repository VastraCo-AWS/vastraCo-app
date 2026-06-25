from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq AI credentials — injected via Secrets Manager CSI Driver on EKS,
    # or set in .env for local development.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Inter-service URLs (injected via docker-compose environment block, not .env)
    PRODUCT_SERVICE_URL: str = "http://product-service:3002"
    ORDER_SERVICE_URL: str = "http://order-service:3003"

    # JWT secret — must match the value used by user-service
    JWT_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
