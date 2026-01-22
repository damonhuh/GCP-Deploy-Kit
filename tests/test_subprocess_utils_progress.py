from __future__ import annotations

import io
import sys
import time

import pytest

from deploy_kit.subprocess_utils import run_command


class _FakeTty(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self._lock = None

    def isatty(self) -> bool:  # type: ignore[override]
        return True


_BRAILLE_FRAMES = {"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}


def _contains_braille_spinner(text: str) -> bool:
    return any(ch in text for ch in _BRAILLE_FRAMES)


def test_stream_output_shows_progress_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    stream_output=True 인 경우에도, 일정 시간 출력이 없으면 진행표시(⠙ 등)가 렌더링되어야 한다.
    """
    fake_err = _FakeTty()
    fake_out = io.StringIO()
    monkeypatch.setattr(sys, "stderr", fake_err)
    monkeypatch.setattr(sys, "stdout", fake_out)

    cmd = [
        sys.executable,
        "-c",
        "import time; time.sleep(0.2); print('done')",
    ]

    result = run_command(
        cmd,
        stream_output=True,
        timeout=5,
        spinner_message="Test stream progress",
        show_progress=True,
        progress_style="braille",
        progress_idle_seconds=0.05,
        progress_interval=0.02,
    )

    assert result.returncode == 0
    stderr_text = fake_err.getvalue()
    assert _contains_braille_spinner(stderr_text), stderr_text


def test_capture_mode_shows_progress_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    capture 모드(stream_output=False)에서도, 오래 걸리면 진행표시가 렌더링되어야 한다.
    """
    fake_err = _FakeTty()
    monkeypatch.setattr(sys, "stderr", fake_err)

    cmd = [
        sys.executable,
        "-c",
        "import time; time.sleep(0.2)",
    ]

    result = run_command(
        cmd,
        stream_output=False,
        timeout=5,
        spinner_message="Test capture progress",
        show_progress=True,
        progress_style="braille",
        progress_idle_seconds=0.05,
        progress_interval=0.02,
    )

    assert result.returncode == 0
    stderr_text = fake_err.getvalue()
    assert _contains_braille_spinner(stderr_text), stderr_text

