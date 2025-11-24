"""
Logging configuration for Sambandha API
"""
import io
import logging
import sys
from pathlib import Path


def _ensure_utf8_stdio():
    """Try to make sys.stdout/stderr UTF-8 encoded (works on Python 3.7+).

    If reconfigure() is available (Python >=3.7), use it. Otherwise, wrap the
    underlying buffer with a TextIOWrapper. Fail silently if neither works.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        # If anything goes wrong, don't rise during logger setup.
        pass


def setup_logging():
    """Configure logging for the application"""
    # Ensure console streams use UTF-8 where possible (prevents UnicodeEncodeError
    # when logging emojis on Windows consoles using cp1252)
    _ensure_utf8_stdio()

    # Create a logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # File handler for all logs (UTF-8)
    sambandha_log_path = logs_dir / "sambandha.log"
    if not any(getattr(h, "baseFilename", None) == str(sambandha_log_path) for h in root_logger.handlers):
        file_handler = logging.FileHandler(sambandha_log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    # Console handler for development (stdout)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout for h in
               root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    # Security handler for security events (separate logger)
    security_log_path = logs_dir / "security.log"
    security_logger = logging.getLogger("security")
    if not any(getattr(h, "baseFilename", None) == str(security_log_path) for h in security_logger.handlers):
        security_handler = logging.FileHandler(security_log_path, encoding="utf-8")
        security_handler.setFormatter(formatter)
        security_handler.setLevel(logging.WARNING)
        security_logger.addHandler(security_handler)

    return root_logger, security_logger


# Initialize loggers
logger, security_logger = setup_logging()