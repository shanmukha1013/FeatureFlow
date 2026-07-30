"""
Exports schemas for management API.
"""
from .pagination import PaginatedResponse
from .queries import PaginationQuery
from .responses import (
    AboutSchema,
    ConfigSchema,
    PlatformOverviewSchema,
    StatisticsSchema,
    SystemInfoSchema,
)

__all__ = [
    "PaginatedResponse", "PaginationQuery", "PlatformOverviewSchema",
    "SystemInfoSchema", "StatisticsSchema", "AboutSchema", "ConfigSchema"
]
