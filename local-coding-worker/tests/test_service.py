from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.service import AdapterService


class Adapter:
    def __init__(self): self.evicted = False
    def inspect(self): return {"available": True}
    def start(self, context): return "handle"
    def health(self, handle): return {"healthy": not self.evicted, "state": "evicted" if self.evicted else "ready"}
    def run(self, handle, request): return {"status": "succeeded"}
    def cancel(self, handle, request_id=None): return {"canceled": True}
    def drain(self, handle): return {"draining": True}
    def evict(self, handle): self.evicted = True; return {"evicted": True}
    def usage(self, handle): return {"runs": 0}
    def quiescent(self, handle): return self.evicted


class Resources:
    def __init__(self): self.released = False
    def reserve_service(self, **kwargs): return "owner", ["gpu:uuid"]
    def set_priority(self, *args): return True
    def preempt_requested(self, *args): return False
    def heartbeat(self, *args): pass
    def release(self, *args): self.released = True


class ServiceTests(unittest.TestCase):
    def test_idle_ttl_evicts_and_quiescence_is_observable(self):
        with tempfile.TemporaryDirectory() as temporary:
            resources, adapter = Resources(), Adapter()
            service = AdapterService(resource_coordinator=resources, project_root=Path(temporary), resource_poll_seconds=.01)
            service.register("llama", adapter)
            handle = service.start("llama", {"resource_request": {"ids": ["gpu:uuid"]},
                "service_profile": {"idle_ttl_seconds": .02}})
            deadline = time.monotonic() + 1
            while not adapter.evicted and time.monotonic() < deadline: time.sleep(.01)
            self.assertTrue(service.wait_for_quiescence("llama", handle, timeout_seconds=.1))
            self.assertTrue(resources.released)

    def test_existing_uncoordinated_service_remains_compatible(self):
        adapter = Adapter(); service = AdapterService(); service.register("fake", adapter)
        handle = service.start("fake", {})
        self.assertEqual(service.run("fake", handle, {})["status"], "succeeded")
        self.assertTrue(service.evict("fake", handle)["evicted"])


if __name__ == "__main__": unittest.main()
