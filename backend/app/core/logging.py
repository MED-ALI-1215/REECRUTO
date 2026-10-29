import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the entire backend."""
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call at module level: logger = get_logger(__name__)"""
    return logging.getLogger(name)


def log_ai_call(
    logger: logging.Logger,
    *,
    service: str,
    model: str,
    prompt_tokens: int,
    latency_ms: float,
    success: bool,
    error: str | None = None,
) -> None:
    """
    Structured log line for every Groq API call.
    Gives visibility into cost (tokens) and reliability (success rate).
    """
    msg = (
        f"AI_CALL service={service} model={model} "
        f"prompt_tokens={prompt_tokens} latency_ms={latency_ms:.0f} "
        f"success={success}"
    )
    if error:
        msg += f" error={error!r}"
    if success:
        logger.info(msg)
    else:
        logger.error(msg)
