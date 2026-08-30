"""Complete the remaining MCP lifecycle state transition branch."""

from agency_runtime.server.mcp import MCPServer


def test_initialized_notification_before_initialize_is_ignored() -> None:
    server = MCPServer(store=object())
    assert (
        server.dispatch(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
        is None
    )
    assert server.initialize_responded is False
    assert server.initialized is False
