import asyncio
from types import SimpleNamespace

from verifiers.v1.agent import Agent
from verifiers.v1.configs.retries import RetryConfig, RetryRule
from verifiers.v1.trace import Error

RETRIES = RetryConfig(rules=[RetryRule(type="ProviderError", max_retries=2)])
OUTAGE = Error(type="ProviderError", message="Service temporarily unavailable", status_code=502)


def failed(*calls):
    return SimpleNamespace(ok=False, errors=[OUTAGE], calls=list(calls))


def succeeded():
    return SimpleNamespace(ok=True, errors=[], calls=[SimpleNamespace(node=object(), usage=None)])


def run(attempts):
    """Agent.run over scripted attempts; returns the final trace and how many ran."""
    pending = list(attempts)
    agent = SimpleNamespace(_closed=False, config=SimpleNamespace(retries=RETRIES))

    async def run_once(*_):
        return pending.pop(0)

    agent._run_once = run_once
    trace = asyncio.run(Agent.run(agent, task=None))
    return trace, len(attempts) - len(pending)


def test_retries_an_attempt_that_spent_nothing(monkeypatch):
    monkeypatch.setattr("verifiers.v1.agent.backoff", lambda attempt: 0)
    unanswered = SimpleNamespace(node=None, usage=None)
    trace, ran = run([failed(unanswered), succeeded()])
    assert ran == 2
    assert trace.ok
    assert trace.errors == [OUTAGE]


def test_keeps_an_attempt_that_spent_model_calls(monkeypatch):
    # A rerun replaces the whole trace, so the answered call and its cost would vanish.
    monkeypatch.setattr("verifiers.v1.agent.backoff", lambda attempt: 0)
    answered = SimpleNamespace(node=object(), usage=SimpleNamespace(total_tokens=10))
    trace, ran = run([failed(answered), succeeded()])
    assert ran == 1
    assert not trace.ok
    assert trace.calls == [answered]
