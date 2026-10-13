"""FastAPI application entry point, CORS middleware, and standard error handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup and handle lifespan events."""
    init_db()
    yield


app = FastAPI(
    title="Food Bank Volunteer Booking API", version="1.0.0", lifespan=lifespan
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
        details.append({"field": loc.replace("body.", ""), "message": msg})

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
