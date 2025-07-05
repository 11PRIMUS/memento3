import structlog
import logging
import sys
from typing import Any, Dict
from app.core.config import settings

def setup()-> None:
    """structured logging for web app"""
    processors=[
        structlog.stlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    #renderer
    if settings.DEBUG:
        processors.append(structlog.dev.ConsoleRenderer())

    else:
        processors.append(structlog.processors.JSONRenderer())
    
    #configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    #configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.INFO)

def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("api")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # log request
            self.logger.info(
                "Request started",
                method=scope["method"],
                path=scope["path"],
                client=scope.get("client", ["unknown", 0])[0]
            )
        
        await self.app(scope, receive, send)
    