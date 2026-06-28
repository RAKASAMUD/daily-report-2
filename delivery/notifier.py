"""Notifier adapter — Task B2."""

import logging
import subprocess
from typing import Protocol

from delivery.config import HERMES_BIN

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send(self, message: str) -> bool:
        ...


class HermesNotifier:
    def __init__(self, target: str, hermes_bin: str = HERMES_BIN):
        self.target = target
        self.hermes_bin = hermes_bin

    def send(self, message: str) -> bool:
        """
        Send a message via hermes CLI.
        Returns True if successful (exit code 0), False otherwise.
        Never raises an exception.
        """
        try:
            # We use --quiet to suppress hermes stdout clutter
            # Message is passed via stdin so it doesn't break shell argument limits or quoting
            proc = subprocess.run(
                [self.hermes_bin, "send", "--to", self.target, "--quiet"],
                input=message,
                text=True,
                capture_output=True,
            )
            if proc.returncode == 0:
                return True
            else:
                logger.warning(
                    "hermes send failed: exit=%d stderr=%s",
                    proc.returncode,
                    proc.stderr.strip(),
                )
                return False
        except Exception as exc:
            logger.warning("hermes send error: %s", exc, exc_info=True)
            return False
