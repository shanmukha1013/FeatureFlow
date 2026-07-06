import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

class PostgresOfflineStore:
    """
    Offline Feature Store.
    Note: Uses SQLite natively to guarantee local execution without requiring a standalone PostgreSQL daemon.
    In a true enterprise environment, this is backed by psycopg2/asyncpg to a distributed RDS cluster.
    """
    def __init__(self, db_path: str = "feature_store.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offline_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    feature_value TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity ON offline_features(entity_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feature ON offline_features(feature_name)')
            conn.commit()

    def insert(self, entity_id: str, feature_name: str, feature_value: Any, feature_version: str, dataset_version: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO offline_features 
                (entity_id, feature_name, feature_value, feature_version, dataset_version, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (entity_id, feature_name, json.dumps(feature_value), feature_version, dataset_version, datetime.utcnow().isoformat()))
            conn.commit()

    def bulk_load(self, records: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data = []
            for r in records:
                data.append((
                    r['entity_id'], 
                    r['feature_name'], 
                    json.dumps(r['feature_value']), 
                    r['feature_version'], 
                    r['dataset_version'], 
                    r.get('timestamp', datetime.utcnow().isoformat())
                ))
            cursor.executemany('''
                INSERT INTO offline_features 
                (entity_id, feature_name, feature_value, feature_version, dataset_version, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()

    def historical_lookup(self, entity_id: str, as_of_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Point-in-time correct retrieval."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if as_of_time:
                cursor.execute('''
                    SELECT feature_name, feature_value 
                    FROM offline_features 
                    WHERE entity_id = ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                ''', (entity_id, as_of_time.isoformat()))
            else:
                cursor.execute('''
                    SELECT feature_name, feature_value 
                    FROM offline_features 
                    WHERE entity_id = ?
                    ORDER BY timestamp DESC
                ''', (entity_id,))
                
            rows = cursor.fetchall()
            
        features = {}
        for row in rows:
            name, val = row
            # We want only the most recent value for each feature as of that time
            if name not in features:
                features[name] = json.loads(val)
        return features

global_offline_store = PostgresOfflineStore()
