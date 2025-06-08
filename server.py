from ast import Call
from cgitb import reset
from email import message
from imp import is_frozen
from math import e
from operator import methodcaller
from optparse import Option
import sys
import json 
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

# configure logging for stderr only 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)



# create the parsed json message with validation
@dataclass
class JsonRpcMessage:
    """
    Respresents a parsed JSON-RPC message with validation.

    Attributes:
        jsonrpc: Protocol version (must be "2.0")
        method: RPC method name (for requests)
        params: Method parameters (optional)
        id: Request identifier (none for notiofications)
        result: Response restult (for response)
        error: Error object (for error responses)
    """
    jsonrpc: str
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    # check if this is a request message
    def is_request(self) -> bool:
        return self.method is not None and self.id is not None

    
    # check if this is a notification
    def is_notification(self) -> bool: 
        return self.method is not None and self.id is None

    # check if this is a response (has id but no method)
    def is_response(self) -> bool:
        return self.method is None and self.id is not None

class MCPServer:
    """
    Main MCP Server implementation with stdio transport.
    """

    def __init__(self):
        """Initialize the server with empty handler registry."""
        # resigrty of method handlers: method_name -> handler_function
        self.handlers: Dict[str, Callable] = {}

        # server state tracking
        self.running = False
        self.initialized = False

        # register built in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register essential MCP protocol handlers"""
        self.handlers['initialize'] = self._handle_initialize
        self.handlers['notifications/intitialized'] = self._handle_initialized
        self.handlers['ping'] = self._handle_ping

    def register_handler(self, method: str, handler: Callable):
        """Register a handler function for a specified RPC method
        
        Args:
            method: The RPC method name (e.g. 'tools/call')
            handler: Functio that takes (params, message_id) and returns the result
        """
        # update the handlers registry
        self.handlers[method] = handler

    def run(self):
        """
        Main event loop implementing the five core steps/

        1. Reads lines from stdin
        2. Parses each line as JSON
        3. Dispatches to appropriate handlers
        4. Writes JSON resonses to stdout
        5. Flushes stdout after each message
        """

        logging.info("Starting MCP server event loop")
        self.running = True

        try:
            while self.running:
                # 1. read lines from stdin
                raw_line = self._read_line_from_stdin()
                if raw_line is None:
                    # EOF reached = client closed connection
                    logging.info("EOF reached on stdin, shutting down")
                    break

                # 2. parse each line as JSON
                message = self._parse_json_message(raw_line)
                if message is None:
                    # parsing failed - continue to next message
                    continue

                # 3. dispatch appropriate event handlers
                response = self._dispatch_message(message)

                # 4. write JSON response to stdout (if response is needed)
                if response is not None:
                    self._write_response_to_stdout(response)

                # 5. Flush stdout after each message
                self._flush_stdout()

        except KeyboardInterrupt:
            logger.info("Recieved keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f'Unexpected error in the event loop: {e}', exc_info=True)
        finally:
            self._cleanup()
        

    def _read_line_from_stdin(self) -> Optional[str]:
        """
        STEP 1: First we need to read a complete line from stdin.

        Returns:
            The line as a string (without newline), or None if EOF

        Notes: 
            - Blocks until a complete line is available
            - Return None on EOF (client disconnected)
            - Handles encoding issues gracefully
        """

        try: 
            
            line = sys.stdin.readline()
            if not line:
                return None

            # strip the new line character
            line = line.rstrip('\n\r')

            # skip empty lines
            if not line.strip():
                logger.debug("Skipping empty line")
                return self._read_line_from_stdin()
            
            logger.debug(f'Read line: {line[:100]}...')
            return line

        except UnicodeDecodeError as e:
            logger.error(f"Uniconde decode error reading stdin: {e}")
            return self._read_line_from_stdin() # try next line
        except Exception as e:
            logger.error(f"Error reading line from stdin: {e}")
            return None

    def _parse_json_message(self, raw_line: str) -> Optional[JsonRpcMessage]:
        """
        STEP 2: After reading the complete line from stdin, we parse as a JSON-RPC message.

        Args:
            raw_line: The raw string from stdin

        Returns:
            Parsed JsonRpcMessage object, or None if parsing fails
        
        Notes:
            - Validates JSON-RPC 2.0 format
            - Logs parsing errors but continues processing
            - Returns None for invalid messages
        """
        try:
            # parse the JSON
            data = json.loads(raw_line)
            logger.debug(f"Parsed JSON: {data}")

            # validate JSON-RPC format
            if not isinstance(data, dict):
                logger.error("Message is not a JSON object")
                return None

            if data.get('jsonrpc') != '2.0':
                logger.error(f"Invalid jsonrpc version: {data.get('jsonrpc')}")
                return None

            # create JsonRpcMessage object
            message = JsonRpcMessage(
                jsonrpc=data['jsonrpc'],
                method=data.get('method'),
                params=data.get('params'),
                id=data.get('id'),
                result=data.get('result'),
                error=data.get('error')
            )

            logger.debug(f"Created message: request={message.is_request()}, "
                        f"notification={message.is_notification()}, "
                        f"response={message.is_response()}")

            return message

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Invalid JSON line: {raw_line}")
            return None
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None

        
    def _dispatch_message(self, message: JsonRpcMessage) -> Optional[Dict[str, Any]]:
        """
        STEP 3: Dispatch message to the appropriate handler.

        Args:
            message: The parsed JSON-RPC message

        Returns:
            Response dictionary to send back, or None for notifications
        
        Notes: 
            - Routes requests to registered handlers
            - Handles method not found errors
            - Generates proper JSON-RPC error responses
            - Notifications don't generate responses
        """
        if message.is_response():
            # this is a response to our request - shouldn't happen in server. Ignore it
            logger.warning("Received response message - ignoring")
            return None
        
        if not (message.is_request() or message.is_notification()):
            logger.error("Message is neither a request or a notification")
            return None

        method = message.method
        logger.info(f"Dispatch method: {method}")

        # check if we have a handler for this method
        if method not in self.handlers:
            logger.error(f"Not handler for method: {method}")

            # only send error response for request (not notifications)
            if message.is_request():
                return self._create_error_response(
                    message.id,
                    -32601,
                    f"Method not found: {method}"
                )
            return None

        try:
            # call the handler
            hander = self.handlers[method]
            result = hander(message.params, message.id)

            # only send a response for requests, not notifications
            if message.is_request():
                return self._create_success_response(message.id, result)
            return None

        except Exception as e:
            logger.error(f"Handler error for {method}: {e}", exc_info=True)

            # also only send an error response for requests
            if message.is_request():
                return self._create_error_response(
                    message.id,
                    -32603,
                    f"Internal error: {str(e)}"
                )
            return None

    def _write_response_to_stdout(self, response: Dict[str, Any]):
        """
        STEP 4: Write JSON response to stdout.

        Args:
            response: The response dictionary to send

        Notes:
            - Serializes response as single line JSON
            - Adds newline terminator
            - Critical: only protocol messages go to stdout
        """
        try: 
            # serialize as single-line JSON 
            json_response = json.dumps(response, separators=(',', ':'))

            # write to stdout with new line terminator
            sys.stdout.write(json_response + '\n')

            logger.debug(f"Sent response: {json_response[:100]}...")
        
        except Exception as e:
            logger.error(f"Error writing response: {e}")
            logger.error(f"Response type: {type(response)}")
            logger.error(f"Response content: {response}")
            
            # try to send back error response
            try:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": response.get('id') if isinstance(response, dict) else None,
                    "error": {
                        "code": -32603,
                        "message": "Response serialization failed"
                    }
                }
                json_error = json.dumps(error_response, separators=(',', ':'))
                sys.stdout.write(json_error + '\n')
            except:
                logger.error("Failed to send error message")
        
    # need to flush so it doesn't just sit in the buffer
    def _flush_stdout(self):
        """
        Step 5: Flush stdout to ensure immediate delivery

        Notes: 
        - Critical for real time communication
        - Ensures messages are sent immediately 
        - Should be called after every message
        """
        try:
            sys.stdout.flush()
            logger.debug("Flushed stdout")
        except Exception as e:
            logger.error(f"Error flushing stdout {e}")

    def _create_success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create a JSON-RPC success response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create a JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }


    def _handle_initialize(self, params: Optional[Dict], request_id: Any) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        logger.info("Handling initialize request")
        
        # Basic server capabilities
        capabilities = {
            "protocol": {
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "example-mcp-server",
                "version": "1.0.0"
            }
        }
        
        self.initialized = True
        return capabilities
    
    def _handle_initialized(self, params: Optional[Dict], request_id: Any) -> None:
        """Handle MCP initialized notification."""
        logger.info("Received initialized notification")
        # This is a notification - no response needed
    
    def _handle_ping(self, params: Optional[Dict], request_id: Any) -> Dict[str, str]:
        """Handle ping request for connectivity testing."""
        logger.debug("Handling ping request")
        return {"status": "pong"}

    def _cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up server resources")
        self.running = False
    
        
if __name__ == "__main__":
    logger.info("Starting MCP Server...")
    server = MCPServer()
    server.run() # Or server.run_event_loop() if you renamed it
    logger.info("MCP Server shut down.")
