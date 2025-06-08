from ast import Call
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

    
        

