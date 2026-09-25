class HealthService:
    @staticmethod
    def get_root_message() -> dict[str, str]:
        return {"message": "InsightFlow API is running"}

    @staticmethod
    def get_health_status() -> dict[str, str]:
        return {"status": "healthy"}
