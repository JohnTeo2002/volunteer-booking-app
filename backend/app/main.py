"""FastAPI application entry point, CORS middleware, and standard error handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import ADMIN_TOKEN, CORS_ORIGINS
from app.db import init_db
from app.rate_limit import limiter
from app.routes.admin import router as admin_router
from app.routes.bookings import router as bookings_router
from app.routes.slots import router as slots_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup and handle lifespan events."""
    if not ADMIN_TOKEN:
        raise RuntimeError(
            "CRITICAL: ADMIN_TOKEN environment variable is unset or empty."
        )
    init_db()
    yield


app = FastAPI(
    title="Food Bank Volunteer Booking API", version="1.0.0", lifespan=lifespan
)
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(admin_router, prefix="/booking", tags=["admin"])
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return rate limit failures in the standard API error envelope."""
    return JSONResponse(
        status_code=429,
        content=error_envelope(
            "RATE_LIMITED",
            "Too many requests. Please try again later.",
            details=None,
        ),
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)


def error_envelope(code: str, message: str, details=None) -> dict:
    """Construct standard error envelope."""
    return {"error": {"code": code, "message": message, "details": details}}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override default 422 validation error with standard error envelope."""
    details = []
    for error in exc.errors():
        loc = ".".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        field = loc.removeprefix("body.").removeprefix("query.").removeprefix("path.")
        details.append({"field": field, "message": msg})

    return JSONResponse(
        status_code=422,
        content=error_envelope(
            "VALIDATION_ERROR", "The request contains invalid data.", details=details
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Override HTTPException to ensure standard error envelope."""
    status_code = exc.status_code
    detail = exc.detail

    code = "INTERNAL_ERROR"
    message = str(detail)
    details = None

    if isinstance(detail, dict):
        code = detail.get("code", "INTERNAL_ERROR")
        message = detail.get("message", str(detail))
        details = detail.get("details", None)
    elif status_code == 404:
        code = "SLOT_NOT_FOUND"
    elif status_code == 403:
        code = "UNAUTHORIZED"
    elif status_code == 409:
        code = "SLOT_FULL"
    elif status_code == 429:
        code = "RATE_LIMITED"

    return JSONResponse(
        status_code=status_code,
        content=error_envelope(code, message, details=details),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions to prevent stack traces from reaching client."""
    return JSONResponse(
        status_code=500,
        content=error_envelope(
            "INTERNAL_ERROR",
            "Something went wrong. Please try again later.",
            details=None,
        ),
    )
