from locust import HttpUser, task, between
import json
import random

class FeatureFlowUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def predict_endpoint(self):
        """Simulate high-throughput inference traffic"""
        payload = {
            "entity_id": f"user_{random.randint(1, 1000)}",
            "features": {
                "age": random.randint(18, 80),
                "income": random.randint(20000, 150000)
            }
        }
        self.client.post("/api/v1/predict", json=payload)

    @task(1)
    def check_health(self):
        """Simulate Kubernetes health probes"""
        self.client.get("/health")
