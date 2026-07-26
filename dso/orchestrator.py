import time
import uuid
from typing import Any

from config import CONFIDENCE_THRESHOLD
from dso.dag import DAGEngine, DAGStep


class SwarmOrchestrator:
    def __init__(self):
        self.engine = DAGEngine()
        self._build_dag()

    def _build_dag(self):
        async def route_fn(ctx: dict, _results: dict) -> dict:
            confidence = ctx.get("confidence", 0.0)
            return {"decision": "escalate" if confidence < CONFIDENCE_THRESHOLD else "route", "confidence": confidence}

        async def match_fn(ctx: dict, results: dict) -> dict:
            task = ctx.get("task", "")
            route = results.get("route", {})
            if route.get("decision") != "route":
                return {"matched": False}
            return {"matched": True, "similar": [], "source": "dso-matcher"}

        async def merge_fn(ctx: dict, results: dict) -> dict:
            match_result = results.get("match", {})
            if not match_result.get("matched"):
                return {"merged": False}
            return {"merged": True, "result": match_result.get("similar", []), "strategy": "majority_vote"}

        async def escalate_fn(ctx: dict, results: dict) -> dict:
            task = ctx.get("task", "")
            return {"escalated": True, "result": f"llm_result:{task[:80]}", "agent": "sint-ada"}

        async def validate_fn(ctx: dict, results: dict) -> dict:
            merged = results.get("merge", {})
            escalated = results.get("escalate", {})
            final = merged if merged.get("merged") else escalated
            return {"valid": True, "output": final.get("result", ""), "validator": "dso-validator"}

        self.engine.add_step(DAGStep("route", [], route_fn))
        self.engine.add_step(DAGStep("match", ["route"], match_fn))
        self.engine.add_step(DAGStep("merge", ["match"], merge_fn))
        self.engine.add_step(DAGStep("escalate", ["route"], escalate_fn))
        self.engine.add_step(DAGStep("validate", ["merge", "escalate"], validate_fn))

    async def process(
        self, task: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())[:8]
        ctx = {"task": task, "confidence": 0.0, **(context or {})}
        start = time.monotonic()

        execution = await self.engine.execute(ctx)

        elapsed = time.monotonic() - start
        route_result = execution.results.get("route", {})
        escalated = route_result.get("decision") == "escalate"

        return {
            "task_id": task_id,
            "status": "completed" if execution.results.get("validate") else "failed",
            "output": execution.results.get("validate", {}).get("output", ""),
            "escalated": escalated,
            "elapsed": round(elapsed, 3),
            "steps": {k: {"status": execution.status[k], "time": round(execution.timings.get(k, 0), 3)} for k in execution.status},
        }

    def export_graph(self) -> dict:
        nodes = []
        edges = []
        for sid, step in self.engine.steps.items():
            nodes.append({"id": sid, "function": step.function.__name__, "timeout": step.timeout, "retry": step.retry})
            for dep in step.depends_on:
                edges.append({"from": dep, "to": sid})
        return {"nodes": nodes, "edges": edges}
