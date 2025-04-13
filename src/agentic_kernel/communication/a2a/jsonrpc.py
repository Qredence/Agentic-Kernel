"""JSON-RPC 2.0 Implementation for A2A Protocol

This module implements the JSON-RPC 2.0 communication layer for the A2A protocol.
It provides functions for creating, parsing, and validating JSON-RPC messages.
"""

import json
import logging
import uuid
from typing import Any

from .types import (
    A2AErrorCode,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
)

logger = logging.getLogger(__name__)


def create_request(
    method: str,
    params: dict[str, Any] | list[Any],
    request_id: str | int | None = None,
) -> JSONRPCRequest:
    """Create a JSON-RPC request.
    
    Args:
        method: The method to call
        params: The parameters for the method
        request_id: The request ID (generated if not provided)
        
    Returns:
        A JSON-RPC request object
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
        
    return JSONRPCRequest(
        jsonrpc="2.0",
        method=method,
        params=params,
        id=request_id,
    )


def create_notification(
    method: str,
    params: dict[str, Any] | list[Any],
) -> JSONRPCRequest:
    """Create a JSON-RPC notification (a request without an ID).
    
    Args:
        method: The method to call
        params: The parameters for the method
        
    Returns:
        A JSON-RPC notification object
    """
    return JSONRPCRequest(
        jsonrpc="2.0",
        method=method,
        params=params,
        id=None,
    )


def create_success_response(
    result: Any,
    request_id: str | int,
) -> JSONRPCResponse:
    """Create a successful JSON-RPC response.
    
    Args:
        result: The result of the method call
        request_id: The ID of the request being responded to
        
    Returns:
        A JSON-RPC response object
    """
    return JSONRPCResponse(
        jsonrpc="2.0",
        result=result,
        id=request_id,
    )


def create_error_response(
    error_code: int | A2AErrorCode,
    error_message: str,
    error_data: Any | None = None,
    request_id: str | int | None = None,
) -> JSONRPCResponse:
    """Create an error JSON-RPC response.
    
    Args:
        error_code: The error code
        error_message: The error message
        error_data: Additional error data
        request_id: The ID of the request being responded to
        
    Returns:
        A JSON-RPC response object
    """
    return JSONRPCResponse(
        jsonrpc="2.0",
        error=JSONRPCError(
            code=error_code,
            message=error_message,
            data=error_data,
        ),
        id=request_id,
    )


def parse_request(request_data: str | bytes | dict[str, Any]) -> tuple[JSONRPCRequest | None, JSONRPCResponse | None]:
    """Parse a JSON-RPC request.
    
    Args:
        request_data: The request data to parse
        
    Returns:
        A tuple of (request, error_response). If parsing succeeds, request will be a JSONRPCRequest
        and error_response will be None. If parsing fails, request will be None and error_response
        will be a JSONRPCResponse containing the error.
    """
    # Parse JSON if needed
    if isinstance(request_data, (str, bytes)):
        try:
            request_dict = json.loads(request_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON-RPC request: {e}")
            return None, create_error_response(
                A2AErrorCode.PARSE_ERROR,
                f"Invalid JSON: {str(e)}",
                request_id=None,
            )
    else:
        request_dict = request_data
    
    # Validate request
    try:
        # Check for required fields
        if "jsonrpc" not in request_dict:
            return None, create_error_response(
                A2AErrorCode.INVALID_REQUEST,
                "Missing 'jsonrpc' field",
                request_id=request_dict.get("id"),
            )
        
        if request_dict["jsonrpc"] != "2.0":
            return None, create_error_response(
                A2AErrorCode.INVALID_REQUEST,
                f"Invalid jsonrpc version: {request_dict['jsonrpc']}",
                request_id=request_dict.get("id"),
            )
        
        if "method" not in request_dict:
            return None, create_error_response(
                A2AErrorCode.INVALID_REQUEST,
                "Missing 'method' field",
                request_id=request_dict.get("id"),
            )
        
        # Create request object
        request = JSONRPCRequest(
            jsonrpc=request_dict["jsonrpc"],
            method=request_dict["method"],
            params=request_dict.get("params", {}),
            id=request_dict.get("id"),
        )
        
        return request, None
    
    except Exception as e:
        logger.error(f"Failed to validate JSON-RPC request: {e}")
        return None, create_error_response(
            A2AErrorCode.INVALID_REQUEST,
            f"Invalid request: {str(e)}",
            request_id=request_dict.get("id"),
        )


def parse_response(response_data: str | bytes | dict[str, Any]) -> tuple[JSONRPCResponse | None, Exception | None]:
    """Parse a JSON-RPC response.
    
    Args:
        response_data: The response data to parse
        
    Returns:
        A tuple of (response, error). If parsing succeeds, response will be a JSONRPCResponse
        and error will be None. If parsing fails, response will be None and error will be an Exception.
    """
    # Parse JSON if needed
    if isinstance(response_data, (str, bytes)):
        try:
            response_dict = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON-RPC response: {e}")
            return None, e
    else:
        response_dict = response_data
    
    # Validate response
    try:
        # Check for required fields
        if "jsonrpc" not in response_dict:
            return None, ValueError("Missing 'jsonrpc' field")
        
        if response_dict["jsonrpc"] != "2.0":
            return None, ValueError(f"Invalid jsonrpc version: {response_dict['jsonrpc']}")
        
        if "id" not in response_dict:
            return None, ValueError("Missing 'id' field")
        
        if "result" not in response_dict and "error" not in response_dict:
            return None, ValueError("Missing 'result' or 'error' field")
        
        if "result" in response_dict and "error" in response_dict:
            return None, ValueError("Both 'result' and 'error' fields are present")
        
        # Create response object
        if "result" in response_dict:
            response = JSONRPCResponse(
                jsonrpc=response_dict["jsonrpc"],
                result=response_dict["result"],
                id=response_dict["id"],
            )
        else:
            error_dict = response_dict["error"]
            if not isinstance(error_dict, dict):
                return None, ValueError(f"Invalid error object: {error_dict}")
            
            if "code" not in error_dict:
                return None, ValueError("Missing 'code' field in error object")
            
            if "message" not in error_dict:
                return None, ValueError("Missing 'message' field in error object")
            
            response = JSONRPCResponse(
                jsonrpc=response_dict["jsonrpc"],
                error=JSONRPCError(
                    code=error_dict["code"],
                    message=error_dict["message"],
                    data=error_dict.get("data"),
                ),
                id=response_dict["id"],
            )
        
        return response, None
    
    except Exception as e:
        logger.error(f"Failed to validate JSON-RPC response: {e}")
        return None, e