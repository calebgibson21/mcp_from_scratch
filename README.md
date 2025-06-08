# MCP Server from Scratch

This project is a Python-based implementation of a Model Context Protocol (MCP) server. It handles communication with an MCP client using JSON-RPC 2.0 messages exchanged via standard input (stdin) and standard output (stdout).

## Features

*   **JSON-RPC 2.0 Compliant:** Adheres to the JSON-RPC 2.0 specification for message formatting and processing.
*   **Stdio Transport:** Uses standard input for receiving requests/notifications and standard output for sending responses/notifications.
*   **Core MCP Handlers:** Implements essential MCP methods:
    *   `initialize`: To set up the server session.
    *   `notifications/initialized`: To confirm initialization.
    *   `ping`: A simple keep-alive/test method.
*   **Extensible:** Designed to allow easy registration of custom method handlers.
*   **Logging:** Includes basic logging to stderr for monitoring server activity and debugging.

## Requirements

*   Python 3.x

## How to Run

1.  Ensure you have Python 3 installed.
2.  Navigate to the project directory in your terminal.
3.  Execute the server script:
    ```bash
    python server.py
    ```
    The server will start and listen for JSON-RPC messages on stdin.

## How it Works

The server operates in an event loop with the following core steps:

1.  **Read from Stdin:** Reads a line of input from `sys.stdin`.
2.  **Parse JSON:** Parses the incoming line as a JSON object.
3.  **Validate & Dispatch:**
    *   Validates if the message conforms to the JSON-RPC 2.0 structure.
    *   Identifies the method call or notification.
    *   Dispatches the message to the appropriate registered handler function.
4.  **Process & Respond:** The handler processes the request and returns a result or error.
5.  **Write to Stdout:** If a response is generated (i.e., for requests, not notifications), it's formatted as a JSON-RPC response and written to `sys.stdout`.
6.  **Flush Stdout:** Ensures the message is immediately sent to the client.

## Protocol

The server communicates using JSON-RPC 2.0. Key message types handled:

*   **Requests:** Expect a response. Must include `jsonrpc: "2.0"`, `method`, and `id`. `params` are optional.
*   **Notifications:** Do not expect a response. Must include `jsonrpc: "2.0"` and `method`. `id` must be absent. `params` are optional.
*   **Responses:** Sent in reply to requests. Must include `jsonrpc: "2.0"`, `id` (matching the request), and either `result` or `error`.

### Built-in Methods

*   `initialize(params, message_id)`: Handles the client's initialization request.
*   `notifications/initialized(params, message_id)`: Handles the client's confirmation that it has initialized.
*   `ping(params, message_id)`: Responds with a simple "pong" or echoes parameters, useful for testing connectivity.

## Extending the Server

You can add custom functionality by registering new handlers:

```python
# In server.py or a module imported by it

def my_custom_method_handler(params: Optional[Dict[str, Any]], message_id: Optional[Any]) -> Any:
    # Your custom logic here
    logger.info(f"Handling my_custom_method with params: {params}")
    return {"status": "success", "data_received": params}

# ... in your server setup ...
# server = MCPServer()
# server.register_handler("myCustomNamespace/myCustomMethod", my_custom_method_handler)
```

Clients can then send requests or notifications for `"myCustomNamespace/myCustomMethod"`.

## Testing

This MCP server can be tested in several ways:

*   **Manual Testing:**
    *   Run `python server.py`.
    *   Manually type or paste JSON-RPC messages into the terminal (stdin).
    *   Observe the JSON-RPC responses printed to the terminal (stdout).
    *   Example `ping` request:
        ```json
        {"jsonrpc": "2.0", "method": "ping", "params": {"data": "hello"}, "id": 1}
        ```
    *   Expected `ping` response:
        ```json
        {"jsonrpc": "2.0", "result": {"message": "pong", "received_params": {"data": "hello"}}, "id": 1}
        ```

*   **Automated Client Scripts:**
    *   Write a client script (e.g., in Python or another language) that spawns `server.py` as a subprocess.
    *   The client script can send JSON-RPC messages to the server's stdin and read/assert responses from its stdout.

*   **Unit Tests:**
    *   Individual components of the server, like the `JsonRpcMessage` class or specific handlers, can be unit-tested directly by instantiating them and calling their methods with test data.

## Logging

The server uses Python's `logging` module. By default, logs are written to `sys.stderr`. This includes information about server startup, received messages, dispatched handlers, and any errors.
