"""Logging setup — Task D3.

Call setup_logging() once at program start (from main()).
Safe to call multiple times — idempotent (no duplicate handlers).
"""

import logging
import os
import sys

_LOGGER_NAME = "data_layer"
_FMT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(logfile: str = "data/data_layer.log") -> None:
    """
    Configure the ``data_layer`` logger with a FileHandler and a StreamHandler.

    Idempotent: if handlers of each type are already attached, they are not
    added again. This makes it safe to call from tests or from code that may
    be imported multiple times.

    Parameters
    ----------
    logfile : str
        Path to the log file. Parent directories are created if needed.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    # ---- FileHandler -------------------------------------------------------
    existing_files = {
        h.baseFilename
        for h in logger.handlers
        if isinstance(h, logging.FileHandler)
    }
    if logfile not in existing_files:
        os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # ---- StreamHandler (stdout) --------------------------------------------
    has_stream = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )
    if not has_stream:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
