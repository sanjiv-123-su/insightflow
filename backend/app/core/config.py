import os


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "InsightFlow API")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    DESCRIPTION: str = os.getenv(
        "DESCRIPTION",
        "InsightFlow API - Analytics and Data Platform Backend",
    )


settings = Settings()
