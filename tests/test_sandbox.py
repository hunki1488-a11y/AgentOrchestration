import resource

from src.agent.sandbox import AgentSandbox, ResourceLimits


class TestAgentSandboxLimits:
    def test_disk_limit_is_not_enabled_by_default(self):
        limits = ResourceLimits()

        assert limits.disk_mb is None

    def test_apply_limits_enforces_explicit_disk_limit(self, monkeypatch):
        calls = []

        def fake_setrlimit(limit, values):
            calls.append((limit, values))

        monkeypatch.setattr(resource, "setrlimit", fake_setrlimit)

        sandbox = AgentSandbox()
        sandbox.apply_limits("agent-1", ResourceLimits(cpu_time=10, memory_mb=64, disk_mb=5))

        assert (resource.RLIMIT_FSIZE, (5 * 1024 * 1024, 5 * 1024 * 1024)) in calls
