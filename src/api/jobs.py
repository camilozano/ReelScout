import threading
import uuid
from typing import Optional, Dict, Any, List


class Job:
    def __init__(self, job_id: str, job_type: str):
        self.job_id = job_id
        self.job_type = job_type  # "collect" | "analyze"
        self.status = "pending"   # "pending" | "running" | "done" | "error"
        self.events: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._lock = threading.Lock()

    def add_event(self, phase: str, current: int, total: int, message: str) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        with self._lock:
            self.events.append(
                {
                    "phase": phase,
                    "current": current,
                    "total": total,
                    "pct": pct,
                    "message": message,
                }
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job_type: str) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, job_type=job_type)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)


job_store = JobStore()
