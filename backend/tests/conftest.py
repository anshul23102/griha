import os
import tempfile

# Tests must never share the dev server's audit log and keys.
os.environ.setdefault("GRIHA_DATA_DIR", tempfile.mkdtemp(prefix="griha-test-"))
os.environ.setdefault("GRIHA_ORCHESTRATOR", "inline")
os.environ.setdefault("GRIHA_RETENTION_HOLD", "0")   # tests use synthetic cases; the hold itself is tested explicitly
os.environ.setdefault("GRIHA_WARM_IMPACT", "0")      # the background warm-up would only slow the tests
os.environ.setdefault("GRIHA_LOGIN_LIMIT", "10000")
os.environ.setdefault("GRIHA_API_LIMIT", "100000")
