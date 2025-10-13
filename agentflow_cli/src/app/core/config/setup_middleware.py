import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from .settings import get_settings, logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID and timestamp to each request and response.

    This middleware generates a unique request ID and a timestamp when a request is received.
    It adds these values to the request state and includes them in the response headers.


    Methods:
        dispatch(request: Request, call_next):
            Generates a unique request ID and timestamp, adds them to the request state,
            and includes them in the response headers.

    Returns:
        Response: The HTTP response with added request ID and timestamp headers.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Middleware dispatch method to handle incoming requests.

        This method generates a unique request ID and a timestamp for each incoming request,
        adds them to the request state, and includes them in the response headers for
        logging purposes.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler to be called.

        Returns:
            Response: The HTTP response with added headers for request ID and timestamp.
        """
        # Generate request ID and timestamp
        request_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Add request ID and timestamp to request headers
        request.state.request_id = request_id
        request.state.timestamp = timestamp
        logger.debug(f"Requesting: Request ID: {request_id}, Timestamp: {timestamp}")

        # Proceed with the request
        response = await call_next(request)

        # Add request ID and timestamp to response headers for logging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Timestamp"] = timestamp
        logger.debug(f"Response: Request ID: {request_id}, Timestamp: {timestamp}")

        return response


def setup_middleware(app: FastAPI):
    """
    Set up middleware for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.

    Middleware:
        - CORS: Configured based on settings.ORIGINS.
        - TrustedHost: Configured with allowed hosts from settings.ALLOWED_HOST.
        - GZip: Applied with a minimum size of 1000 bytes.
    """
    settings = get_settings()
    # init cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOST.split(","))

    app.add_middleware(RequestIDMiddleware)

    # Note: If you need streaming responses, you should not use GZipMiddleware.
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.debug("Middleware set up")
