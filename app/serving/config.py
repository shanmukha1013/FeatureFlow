"""
Configuration parameters for the Serving Layer.
"""

class ServingConfig:
    api_version: str = "v1"
    platform_version: str = "1.0.0"
    title: str = "FeatureFlow Serving API"

serving_config = ServingConfig()
