import logging

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.main import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# RLS Error Handlers will be added after app creation


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


# RLS Error Handlers
@app.exception_handler(HTTPException)
async def rls_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions with RLS-specific error messages."""
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        # Check if this is an RLS-related permission error
        if (
            "owner" in str(exc.detail).lower()
            or "permission" in str(exc.detail).lower()
        ):
            logger.warning(f"RLS access denied for user: {request.url}")
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": "Access denied: You can only access your own data",
                    "error_code": "RLS_ACCESS_DENIED",
                    "request_id": request.headers.get("x-request-id", "unknown"),
                },
            )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(ValueError)
async def rls_value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions that might be RLS-related."""
    error_message = str(exc)

    # Check if this is an RLS ownership error
    if "owner" in error_message.lower() or "belongs to" in error_message.lower():
        logger.warning(f"RLS ownership violation: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "Access denied: You can only access your own data",
                "error_code": "RLS_OWNERSHIP_VIOLATION",
                "request_id": request.headers.get("x-request-id", "unknown"),
            },
        )

    # Generic ValueError handling
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": error_message}
    )


@app.exception_handler(RequestValidationError)
async def rls_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with RLS context."""
    # Log validation errors for debugging
    logger.debug(f"Validation error on {request.url}: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "request_id": request.headers.get("x-request-id", "unknown"),
        },
    )
