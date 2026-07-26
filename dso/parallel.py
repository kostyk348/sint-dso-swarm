import asyncio
import json
import time
import uuid
from typing import Any

from dso.orchestrator import SwarmOrchestrator
from dso.stats import SwarmStats


def _majority_vote(results: list[dict]) -> dict:
    if not results:
        return {"merged": False, "result": None}
    outputs = [r.get("output", "") for r in results if r.get("status") == "completed"]
    if not outputs:
        return {"merged": False, "result": None}
    from collections import Counter
    counts = Counter(outputs)
    winner = counts.most_common(1)[0][0]
    return {
        "merged": True,
        "result": winner,
        "strategy": "majority_vote",
        "total": len(results),
        "agreement": counts[winner] / len(results),
    }


def _weighted_merge(results: list[dict]) -> dict:
    if not results:
        return {"merged": False, "result": None}
    outputs = [(r.get("output", ""), 1.0 - r.get("elapsed", 0.5) / 10.0)
               for r in results if r.get("status") == "completed"]
    if not outputs:
        return {"merged": False, "result": None}
    from collections import defaultdict
    scores: dict[str, float] = defaultdict(float)
    for out, w in outputs:
        scores[out] += w
    winner = max(scores, key=scores.get)
    return {
        "merged": True,
        "result": winner,
        "strategy": "weighted_merge",
        "total": len(results),
    }


async def fan_out_fan_in(
    tasks_json: str, merge_strategy: str = "majority_vote"
) -> dict[str, Any]:
    try:
        tasks = json.loads(tasks_json)
    except json.JSONDecodeError:
        return {"status": "error", "error": "invalid JSON in tasks_json"}

    if not isinstance(tasks, list):
        return {"status": "error", "error": "tasks_json must be a JSON array"}

    parallel_id = str(uuid.uuid4())[:8]
    orchestrator = SwarmOrchestrator()
    stats = SwarmStats()
    start = time.monotonic()

    async def run_single(task_item: str | dict) -> dict:
        if isinstance(task_item, dict):
            t = task_item.get("task", json.dumps(task_item))
            ctx = {k: v for k, v in task_item.items() if k != "task"}
        else:
            t = str(task_item)
            ctx = {}
        result = await orchestrator.process(t, ctx)
        stats.record(result["task_id"], len(t), result["escalated"], result["elapsed"])
        return result

    results = await asyncio.gather(*[run_single(t) for t in tasks])

    merge_fn = _majority_vote if merge_strategy == "majority_vote" else _weighted_merge
    merged = merge_fn(results)

    elapsed = time.monotonic() - start

    return {
        "parallel_id": parallel_id,
        "tasks": len(tasks),
        "completed": sum(1 for r in results if r.get("status") == "completed"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "elapsed": round(elapsed, 3),
        "merge_strategy": merge_strategy,
        "merged_output": merged.get("result", ""),
        "agreement": merged.get("agreement", 0.0),
        "results": results,
    }
