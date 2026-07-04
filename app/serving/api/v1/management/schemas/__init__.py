"""
Exports schemas for management API.
"""
from .pagination import PaginatedResponse
from .queries import PaginationQuery
from .responses import (
    PlatformOverviewSchema, SystemInfoSchema, StatisticsSchema,
    AboutSchema, ConfigSchema
)

__all__ = [
    "PaginatedResponse", "PaginationQuery", "PlatformOverviewSchema",
    "SystemInfoSchema", "StatisticsSchema", "AboutSchema", "ConfigSchema"
]
