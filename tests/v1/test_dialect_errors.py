import pytest

from verifiers.v1.dialects import AnthropicDialect, ChatDialect, ResponsesDialect


def error_type(dialect, status_code: int) -> str:
    return dialect.error_body("boom", status_code=status_code)["error"]["type"]


@pytest.mark.parametrize("dialect", [ChatDialect(), ResponsesDialect()])
def test_openai_errors_follow_status(dialect):
    # Harnesses retry a server error and give up on a malformed request, so a relayed
    # provider outage must not be labelled as the client's fault.
    assert error_type(dialect, 400) == "invalid_request_error"
    assert error_type(dialect, 502) == "server_error"
    assert error_type(dialect, 503) == "server_error"


def test_anthropic_errors_follow_status():
    dialect = AnthropicDialect()
    assert error_type(dialect, 400) == "invalid_request_error"
    assert error_type(dialect, 502) == "api_error"
