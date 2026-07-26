# sint-dso-swarm

**DSO Swarm Orchestrator** — DAG-based deterministic agent coordination layer. Routes tasks through a directed acyclic graph of DSO deterministic agents and decides when to escalate to LLM agents.

## DAG Flow

```
Input → dso-router → [confidence > 0.8?]
  ├─ Yes → dso-matcher → dso-merger → dso-validator → Output
  └─ No  → Escalate to LLM agent → LLM result → dso-validator → Output
```

## Tools

| Tool | Description |
|------|-------------|
| `dso_swarm_process` | Run full swarm DAG on a task |
| `dso_swarm_parallel` | Fan-out tasks, fan-in merge results |
| `dso_swarm_status` | Get status of a swarm execution |
| `dso_swarm_graph` | Export the DAG as JSON |
| `dso_swarm_stats` | Performance stats and token savings |

## Token Savings

```
saved = estimated_llm_tokens - actual_dso_tokens
```

Where `estimated_llm_tokens = task_length × 4 + 1000` and `actual_dso_tokens = 0` for deterministic (non-escalated) paths.
