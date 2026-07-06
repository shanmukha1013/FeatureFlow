import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, List
from app.training.retraining.metadata import RetrainingJob, RetrainingStatus, RetrainingTrigger
from app.data.dataset_registry import global_dataset_registry
from app.monitoring.audit import AuditLogger, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RetrainingManager:
    def __init__(self):
        self._jobs: Dict[str, RetrainingJob] = {}
        self._lock = threading.Lock()

    def start_retraining(self, dataset_name: str, trigger_type: RetrainingTrigger, policy_id: str = "manual") -> str:
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
        job = RetrainingJob(
            job_id=job_id,
            policy_id=policy_id,
            trigger_type=trigger_type,
            dataset_name=dataset_name
        )
        
        with self._lock:
            self._jobs[job_id] = job
            
        AuditLogger.record(AuditEvent(event_name="RETRAINING_STARTED", component="RetrainingManager", severity="INFO", payload={"job_id": job_id, "dataset": dataset_name, "trigger": trigger_type.value}))
        
        # Start in background thread
        thread = threading.Thread(target=self._execute_job, args=(job_id, dataset_name))
        thread.start()
        
        return job_id

    def _execute_job(self, job_id: str, dataset_name: str):
        from app.training.orchestrator import TrainingOrchestrator
        from app.serving.dependencies import _training_registry
        
        try:
            dataset_meta = global_dataset_registry.get(dataset_name)
            
            # Store the current champion before training to know if promotion occurred
            old_champion = None
            for m_id in _training_registry.list_models():
                existing = _training_registry.get(m_id)
                if existing.dataset_version == dataset_meta.version and existing.lifecycle_state.value == "CHAMPION":
                    old_champion = m_id
                    break
            
            orchestrator = TrainingOrchestrator()
            orchestrator.execute(dataset_meta)
            
            # Check if a new champion was promoted
            new_champion = None
            for m_id in _training_registry.list_models():
                existing = _training_registry.get(m_id)
                if existing.dataset_version == dataset_meta.version and existing.lifecycle_state.value == "CHAMPION":
                    new_champion = m_id
                    break
                    
            promoted = (new_champion != old_champion) and (new_champion is not None)
            
            with self._lock:
                job = self._jobs[job_id]
                updated_job = RetrainingJob(
                    job_id=job.job_id,
                    policy_id=job.policy_id,
                    trigger_type=job.trigger_type,
                    dataset_name=job.dataset_name,
                    status=RetrainingStatus.COMPLETED,
                    start_time=job.start_time,
                    end_time=datetime.utcnow(),
                    champion_promoted=promoted,
                    new_champion_id=new_champion
                )
                self._jobs[job_id] = updated_job
                
            AuditLogger.record(AuditEvent(event_name="RETRAINING_COMPLETED", component="RetrainingManager", severity="INFO", payload={"job_id": job_id, "promoted": promoted, "champion": new_champion}))
            
        except Exception as e:
            with self._lock:
                job = self._jobs[job_id]
                updated_job = RetrainingJob(
                    job_id=job.job_id,
                    policy_id=job.policy_id,
                    trigger_type=job.trigger_type,
                    dataset_name=job.dataset_name,
                    status=RetrainingStatus.FAILED,
                    start_time=job.start_time,
                    end_time=datetime.utcnow(),
                    error_message=str(e)
                )
                self._jobs[job_id] = updated_job
                
            AuditLogger.record(AuditEvent(event_name="RETRAINING_FAILED", component="RetrainingManager", severity="ERROR", payload={"job_id": job_id, "error": str(e)}))
            logger.error(f"Retraining job {job_id} failed: {e}")

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            # Sort by start_time descending
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda x: x.start_time, reverse=True)
            return [j.to_dict() for j in jobs]
            
    def rollback(self, dataset_name: str) -> bool:
        """Rolls back the current ACTIVE champion to the previously ARCHIVED model with the best accuracy."""
        from app.serving.dependencies import _training_registry
        from app.training.metadata import ModelLifecycleState
        
        active_model = None
        candidates_for_rollback = []
        
        for m_id in _training_registry.list_models():
            m = _training_registry.get(m_id)
            if m.dataset_name() == dataset_name or m.model_id.startswith(f"mdl_{dataset_name}"):
                if m.lifecycle_state == ModelLifecycleState.CHAMPION:
                    active_model = m
                elif m.lifecycle_state == ModelLifecycleState.ARCHIVED:
                    candidates_for_rollback.append(m)
                    
        if not candidates_for_rollback:
            logger.warning(f"No archived models found for dataset {dataset_name} to rollback to.")
            return False
            
        # Find the best archived model
        best_archived = max(candidates_for_rollback, key=lambda m: m.metrics.get('accuracy', 0))
        
        if active_model:
            _training_registry.update_lifecycle_state(active_model.model_id, ModelLifecycleState.ARCHIVED)
            
        _training_registry.update_lifecycle_state(best_archived.model_id, ModelLifecycleState.CHAMPION)
        
        AuditLogger.record(AuditEvent(event_name="ROLLBACK_EXECUTED", component="RetrainingManager", severity="WARNING", payload={"dataset": dataset_name, "rolled_back_from": active_model.model_id if active_model else "None", "rolled_back_to": best_archived.model_id}))
        return True

global_retraining_manager = RetrainingManager()
