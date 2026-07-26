import asyncio
import time
import uuid
from typing import Any, Callable


class DAGStep:
    def __init__(
        self,
        step_id: str,
        depends_on: list[str],
        function: Callable,
        timeout: float = 30.0,
        retry: int = 2,
    ):
        self.id = step_id
        self.depends_on = depends_on
        self.function = function
        self.timeout = timeout
        self.retry = retry


class DAGExecution:
    def __init__(self, dag_id: str):
        self.dag_id = dag_id
        self.results: dict[str, Any] = {}
        self.timings: dict[str, float] = {}
        self.errors: dict[str, str] = {}
        self.status: dict[str, str] = {}


class DAGEngine:
    def __init__(self):
        self.steps: dict[str, DAGStep] = {}

    def add_step(self, step: DAGStep):
        self.steps[step.id] = step

    def _topological_order(self) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def dfs(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            step = self.steps[node_id]
            for dep in step.depends_on:
                if dep in self.steps:
                    dfs(dep)
            order.append(node_id)

        for sid in self.steps:
            dfs(sid)
        return order

    async def execute(
        self, context: dict[str, Any], execution: DAGExecution | None = None
    ) -> DAGExecution:
        dag_id = str(uuid.uuid4())[:8]
        if execution is None:
            execution = DAGExecution(dag_id)

        order = self._topological_order()

        for step_id in order:
            step = self.steps[step_id]
            deps_met = all(
                execution.status.get(d) == "done" for d in step.depends_on
            )
            if not deps_met:
                missing = [d for d in step.depends_on if execution.status.get(d) != "done"]
                execution.status[step_id] = "blocked"
                execution.errors[step_id] = f"dependencies not met: {missing}"
                continue

            execution.status[step_id] = "running"
            start = time.monotonic()

            for attempt in range(step.retry + 1):
                try:
                    result = await asyncio.wait_for(
                        step.function(context, execution.results),
                        timeout=step.timeout,
                    )
                    execution.results[step_id] = result
                    execution.status[step_id] = "done"
                    break
                except Exception as e:
                    execution.status[step_id] = "failed"
                    execution.errors[step_id] = str(e)
                    if attempt < step.retry:
                        await asyncio.sleep(0.5 * (attempt + 1))

            execution.timings[step_id] = time.monotonic() - start

        return execution
