"""Tests for delivery.notifier — Task B2."""

import subprocess
import pytest

from delivery.notifier import HermesNotifier


class TestHermesNotifier:
    def test_send_success_returns_true(self, monkeypatch):
        # We need to capture the arguments to subprocess.run
        captured_args = {}
        
        def fake_run(args, **kwargs):
            captured_args["args"] = args
            captured_args["kwargs"] = kwargs
            # return a completed process with returncode 0
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            
        monkeypatch.setattr(subprocess, "run", fake_run)
        
        notifier = HermesNotifier(target="telegram", hermes_bin="fake_hermes")
        result = notifier.send("hello world")
        
        assert result is True
        assert captured_args["args"] == ["fake_hermes", "send", "--to", "telegram", "--quiet"]
        assert captured_args["kwargs"]["input"] == "hello world"
        assert captured_args["kwargs"]["text"] is True

    def test_send_nonzero_exit_returns_false(self, monkeypatch):
        def fake_run(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="error")
            
        monkeypatch.setattr(subprocess, "run", fake_run)
        
        notifier = HermesNotifier(target="telegram")
        result = notifier.send("hello world")
        assert result is False

    def test_send_exception_returns_false_and_swallows(self, monkeypatch):
        def fake_run(args, **kwargs):
            raise OSError("Command not found")
            
        monkeypatch.setattr(subprocess, "run", fake_run)
        
        notifier = HermesNotifier(target="telegram")
        # Should not raise exception
        result = notifier.send("hello world")
        assert result is False
