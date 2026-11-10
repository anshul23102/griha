"""Process-wide runtime state shared by the API and the workflow worker (they run in one process)."""
import os

STATE: dict = {}
SLA_SECONDS = int(os.environ.get("GRIHA_SLA_SECONDS", "3600"))   # how long a referred case may wait before escalation
