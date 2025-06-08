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
