from enum import Enum
from dataclasses import dataclass

class Role(str, Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    ML_ENGINEER = "ML_ENGINEER"
    VIEWER = "VIEWER"

class Permission(str, Enum):
    DATASET_MANAGEMENT = "DATASET_MANAGEMENT"
    TRAINING = "TRAINING"
    DEPLOYMENT = "DEPLOYMENT"
    MODEL_PROMOTION = "MODEL_PROMOTION"
    MONITORING = "MONITORING"
    DASHBOARD = "DASHBOARD"
    MANAGEMENT_API = "MANAGEMENT_API"

@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    role: Role
    
ROLE_PERMISSIONS = {
    Role.ADMINISTRATOR: [p for p in Permission],
    Role.ML_ENGINEER: [
        Permission.DATASET_MANAGEMENT,
        Permission.TRAINING,
        Permission.DEPLOYMENT,
        Permission.MONITORING,
        Permission.DASHBOARD,
        Permission.MANAGEMENT_API
    ],
    Role.VIEWER: [
        Permission.MONITORING,
        Permission.DASHBOARD,
        Permission.MANAGEMENT_API
    ]
}
