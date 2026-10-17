import importlib.util
import subprocess
import sys
import time
from pathlib import Path


def _module():
    path = Path(__file__).resolve().parents[2] / "workers" / "media-generation-local" / "execution_store.py"
    spec = importlib.util.spec_from_file_location("res_local_execution_store", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_liveness_probe_does_not_terminate_process():
    module = _module()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        identity = module.process_identity(process.pid)
        assert identity
        assert module.process_matches({"pid": process.pid, "identity": identity})
        time.sleep(0.1)
        assert process.poll() is None
    finally:
        process.kill()
        process.wait(timeout=5)


def test_payload_digest_ignores_only_execution_id():
    module = _module()
    first = module.request_digest({"executionId": "a", "prompt": "one"})
    assert first == module.request_digest({"executionId": "b", "prompt": "one"})
    assert first != module.request_digest({"executionId": "a", "prompt": "two"})


def test_initializing_lease_has_a_grace_period():
    module = _module()
    lease = {"createdAt": time.time(), "executionId": "id"}
    assert module.lease_stale(lease, None, grace_seconds=30) is False
    lease["createdAt"] -= 31
    assert module.lease_stale(lease, None, grace_seconds=30) is True
