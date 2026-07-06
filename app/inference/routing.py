from typing import Dict, Optional
import random
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TrafficRouter:
    """
    Manages traffic splitting between Champion and Challenger models.
    Default is 100% Champion.
    """
    def __init__(self):
        self.champion_id: Optional[str] = None
        self.challenger_id: Optional[str] = None
        # Weight represents the percentage of traffic that goes to the CHAMPION (0.0 to 1.0)
        self.champion_weight: float = 1.0
        
    def configure(self, champion_id: Optional[str], challenger_id: Optional[str], champion_weight: float = 1.0):
        self.champion_id = champion_id
        self.challenger_id = challenger_id
        
        # Enforce bounds
        self.champion_weight = max(0.0, min(1.0, champion_weight))
        
        # If no challenger exists, force 100% to champion
        if not self.challenger_id:
            self.champion_weight = 1.0
            
        logger.info(f"Traffic routing configured: CHAMPION ({self.champion_weight*100}%) -> {self.champion_id}, CHALLENGER ({(1-self.champion_weight)*100}%) -> {self.challenger_id}")

    def select_model(self) -> Optional[str]:
        if not self.champion_id:
            return self.challenger_id # Fallback if only challenger exists for some weird reason
            
        if self.champion_weight >= 1.0 or not self.challenger_id:
            return self.champion_id
            
        # Generate random float between 0.0 and 1.0
        roll = random.random()
        if roll <= self.champion_weight:
            return self.champion_id
        else:
            return self.challenger_id
            
global_traffic_router = TrafficRouter()
