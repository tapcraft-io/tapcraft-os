"""Platform-level defaults for workflow execution guardrails.

These defaults protect users from common misconfigurations like infinite
retry loops and runaway workflows. All values can be overridden per-workflow
via environment variables or workflow config.
"""

import os
from datetime import timedelta


# -- Workflow execution limits ------------------------------------------------

# Max time a workflow can run before Temporal terminates it.
# Prevents forgotten/stuck workflows from running indefinitely.
WORKFLOW_EXECUTION_TIMEOUT = timedelta(
    hours=int(os.getenv("TAPCRAFT_WORKFLOW_TIMEOUT_HOURS", "24"))
)

# Max time a single workflow run attempt can take (excludes retries).
WORKFLOW_RUN_TIMEOUT = timedelta(
    hours=int(os.getenv("TAPCRAFT_WORKFLOW_RUN_TIMEOUT_HOURS", "12"))
)


# -- Activity defaults (applied when user doesn't specify) --------------------

# Default max retry attempts for activities.
# Temporal's default is unlimited. We cap it.
DEFAULT_ACTIVITY_MAX_ATTEMPTS = int(
    os.getenv("TAPCRAFT_DEFAULT_MAX_ATTEMPTS", "10")
)

# Default start-to-close timeout for activities.
DEFAULT_ACTIVITY_TIMEOUT_SECONDS = int(
    os.getenv("TAPCRAFT_DEFAULT_ACTIVITY_TIMEOUT", "300")
)

# Absolute ceiling: even if a user sets higher, we cap at this.
MAX_ACTIVITY_RETRY_ATTEMPTS = int(
    os.getenv("TAPCRAFT_MAX_RETRY_ATTEMPTS", "50")
)


# -- Health monitoring --------------------------------------------------------

# An activity retrying more than this many times is considered "stuck".
STUCK_ACTIVITY_THRESHOLD = int(
    os.getenv("TAPCRAFT_STUCK_THRESHOLD", "10")
)

# A workflow running longer than this is flagged as potentially unhealthy.
LONG_RUNNING_WORKFLOW_THRESHOLD = timedelta(
    hours=int(os.getenv("TAPCRAFT_LONG_RUNNING_HOURS", "6"))
)
