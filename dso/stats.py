import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any

from config import STATS_PATH


@dataclass
class TaskRecord:
    task_id: str
    task_length: int
    escalated: bool
    elapsed: float
    token_savings: int
    timestamp: float


class SwarmStats:
    def __init__(self):
        self.tasks: list[TaskRecord] = []
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
        if os.path.exists(STATS_PATH):
            try:
                with open(STATS_PATH) as f:
                    data = json.load(f)
                    self.tasks = [TaskRecord(**t) for t in data.get("tasks", [])]
            except (json.JSONDecodeError, KeyError):
                self.tasks = []

    def _save(self):
        os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
        with open(STATS_PATH, "w") as f:
            json.dump({"tasks": [asdict(t) for t in self.tasks]}, f, indent=2)

    def record(
        self,
        task_id: str,
        task_length: int,
        escalated: bool,
        elapsed: float,
    ):
        savings = self._compute_savings(task_length, escalated)
        r = TaskRecord(
            task_id=task_id,
            task_length=task_length,
            escalated=escalated,
            elapsed=elapsed,
            token_savings=savings,
            timestamp=time.time(),
        )
        self.tasks.append(r)
        self._save()

    @staticmethod
    def _compute_savings(task_length: int, escalated: bool) -> int:
        from config import TOKEN_ESTIMATE_MULTIPLIER, TOKEN_GENERATION_OVERHEAD
        llm_tokens = task_length * TOKEN_ESTIMATE_MULTIPLIER + TOKEN_GENERATION_OVERHEAD
        if escalated:
            actual = llm_tokens
        else:
            actual = 0
        return llm_tokens - actual

    def summary(self) -> dict[str, Any]:
        n = len(self.tasks)
        if n == 0:
            return {
                "tasks_processed": 0,
                "avg_time": 0.0,
                "escalation_rate": 0.0,
                "total_token_savings": 0,
            }
        total_time = sum(t.elapsed for t in self.tasks)
        escalations = sum(1 for t in self.tasks if t.escalated)
        total_savings = sum(t.token_savings for t in self.tasks)
        return {
            "tasks_processed": n,
            "avg_time": round(total_time / n, 3),
            "escalation_rate": round(escalations / n, 3),
            "total_token_savings": total_savings,
        }
