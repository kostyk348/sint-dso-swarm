import os

DSO_AGENTS = {
    "dso-router": "task:agent",
    "dso-validator": "task:agent",
    "dso-matcher": "task:agent",
    "dso-merger": "task:agent",
    "sint-ada": "task:agent",
    "sint-main": "task:agent",
}

CONFIDENCE_THRESHOLD = 0.8

STATS_PATH = os.path.expanduser("~/.config/opencode/dso/swarm_stats.json")

DAG_DEFAULT_TIMEOUT = 30.0
DAG_MAX_RETRIES = 2

TOKEN_ESTIMATE_MULTIPLIER = 4
TOKEN_GENERATION_OVERHEAD = 1000
