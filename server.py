from fastmcp import FastMCP

from dso.orchestrator import SwarmOrchestrator
from dso.parallel import fan_out_fan_in
from dso.stats import SwarmStats

server = FastMCP("sint-dso-swarm", description="DSO Swarm Orchestrator — DAG-based deterministic agent coordination")
orchestrator = SwarmOrchestrator()
stats = SwarmStats()


@server.tool()
async def dso_swarm_process(task: str, context: str = "{}") -> dict:
    """Run the full swarm DAG on a single task: route → (match+vote|escalate) → validate → output."""
    import json
    ctx = json.loads(context) if isinstance(context, str) else {}
    result = await orchestrator.process(task, ctx)
    stats.record(result["task_id"], len(task), result["escalated"], result["elapsed"])
    return result


@server.tool()
async def dso_swarm_parallel(tasks_json: str, merge_strategy: str = "majority_vote") -> dict:
    """Run multiple tasks through the swarm in parallel (fan-out), then merge results (fan-in)."""
    return await fan_out_fan_in(tasks_json, merge_strategy)


@server.tool()
async def dso_swarm_status(task_id: str) -> dict:
    """Get the status and result of a previously executed swarm task (stub — queries stats log)."""
    summary = stats.summary()
    return {
        "task_id": task_id,
        "found": False,
        "note": "In-memory task lookup not implemented; check stats summary below.",
        "stats": summary,
    }


@server.tool()
async def dso_swarm_graph() -> dict:
    """Export the DAG as JSON with nodes and edges."""
    return orchestrator.export_graph()


@server.tool()
async def dso_swarm_stats() -> dict:
    """Performance stats: tasks processed, avg time, escalation rate, token savings."""
    return stats.summary()


if __name__ == "__main__":
    server.run()
