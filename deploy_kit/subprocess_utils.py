from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from textwrap import shorten
from typing import Mapping, Sequence

from .logging_utils import get_logger


logger = get_logger(__name__)


# -----------------------------
# CLI progress indicator config
# -----------------------------
_cli_progress_lock = threading.Lock()
_cli_show_progress: bool = True
_cli_progress_idle_seconds: float = 2.0
_cli_progress_style: str = "braille"  # braille | ascii
_cli_progress_interval: float = 0.12


def configure_cli_progress(
    *,
    show_progress: bool | None = None,
    idle_seconds: float | None = None,
    style: str | None = None,
    interval: float | None = None,
) -> None:
    """
    전역 CLI 진행 표시 설정.

    주로 CLI 엔트리포인트에서 DeployConfig 값을 한 번 반영하기 위해 사용한다.
    """
    global _cli_show_progress, _cli_progress_idle_seconds, _cli_progress_style, _cli_progress_interval
    with _cli_progress_lock:
        if show_progress is not None:
            _cli_show_progress = bool(show_progress)
        if idle_seconds is not None:
            _cli_progress_idle_seconds = float(idle_seconds)
        if style is not None:
            _cli_progress_style = str(style)
        if interval is not None:
            _cli_progress_interval = float(interval)


def _is_tty(stream) -> bool:  # noqa: ANN001
    try:
        return bool(getattr(stream, "isatty") and stream.isatty())
    except Exception:  # noqa: BLE001
        return False


def _get_progress_defaults() -> tuple[bool, float, str, float]:
    with _cli_progress_lock:
        return (
            _cli_show_progress,
            _cli_progress_idle_seconds,
            _cli_progress_style,
            _cli_progress_interval,
        )


def _parse_env_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_env_float(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _progress_settings_from_env() -> tuple[bool | None, float | None, str | None, float | None]:
    # CLI 쪽에서 DeployConfig를 통해 configure_cli_progress를 호출하지 못하는 경우에도 동작하도록
    # env 기반 설정을 지원한다.
    show = _parse_env_bool("CLI_SHOW_PROGRESS")
    idle = _parse_env_float("CLI_PROGRESS_IDLE_SECONDS")
    style = os.getenv("CLI_PROGRESS_STYLE")
    interval = _parse_env_float("CLI_PROGRESS_INTERVAL_SECONDS")
    return show, idle, style, interval


_BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_ASCII_FRAMES = ["|", "/", "-", "\\"]


def _select_frames(style: str) -> list[str]:
    s = (style or "").strip().lower()
    if s == "ascii":
        return _ASCII_FRAMES
    return _BRAILLE_FRAMES


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:0.1f}s"
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    return f"{minutes}m{sec:02d}s"


def _default_progress_message(cmd: Sequence[str]) -> str:
    return shorten(" ".join(cmd), width=72, placeholder="…")


class _ProgressLine:
    """
    단일 라인 진행 표시(스피너 + 메시지 + 경과시간).
    stderr에만 출력하여 stdout 로그와 섞임을 최소화한다.
    """

    def __init__(self, message: str, *, stream=None, style: str = "braille") -> None:  # noqa: ANN001
        self._message = message
        self._stream = stream if stream is not None else sys.stderr
        self._frames = _select_frames(style)
        self._last_len = 0

    def render(self, frame_idx: int, *, elapsed_seconds: float) -> None:
        frame = self._frames[frame_idx % len(self._frames)]
        elapsed = _format_elapsed(elapsed_seconds)
        text = f"{frame} {self._message}  {elapsed}"
        self._last_len = max(self._last_len, len(text))
        self._stream.write("\r" + text)
        self._stream.flush()

    def clear(self) -> None:
        if self._last_len <= 0:
            return
        self._stream.write("\r" + (" " * self._last_len) + "\r")
        self._stream.flush()


class _IdleProgressIndicator:
    """
    '무출력(idle)' 구간에서만 진행표시를 렌더하는 스피너.
    """

    def __init__(
        self,
        *,
        message: str,
        stream=None,  # noqa: ANN001
        style: str = "braille",
        interval: float = 0.12,
        idle_seconds: float = 2.0,
    ) -> None:
        self._line = _ProgressLine(message, stream=stream, style=style)
        self._interval = max(float(interval), 0.02)
        self._idle_seconds = max(float(idle_seconds), 0.0)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0
        self._last_activity_getter = None  # type: ignore[assignment]
        self._shown = False

    def start(self, *, start_time: float, last_activity_getter) -> None:  # noqa: ANN001
        if self._thread is not None:
            return
        self._start_time = start_time
        self._last_activity_getter = last_activity_getter

        def _run() -> None:
            idx = 0
            while not self._stop.is_set():
                now = time.monotonic()
                last = float(self._last_activity_getter())
                idle = now - last

                if idle < self._idle_seconds:
                    if self._shown:
                        self._line.clear()
                        self._shown = False
                    sleep_for = min(self._interval, max(self._idle_seconds - idle, 0.02))
                    time.sleep(sleep_for)
                    continue

                self._line.render(idx, elapsed_seconds=now - self._start_time)
                self._shown = True
                idx += 1
                time.sleep(self._interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def clear(self) -> None:
        if self._shown:
            self._line.clear()
            self._shown = False

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.clear()


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str


class Spinner:
    """
    간단한 CLI 스피너(로딩 애니메이션).

    - stdout/stderr 출력이 많지 않은 작업에서 '멈춘 것 같은' UX를 방지한다.
    - 출력 스트리밍을 사용하는 명령에서는 스피너를 끄는 것을 권장한다.
    """

    def __init__(self, message: str = "작업 처리 중", *, interval: float = 0.12) -> None:
        self._message = message
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._frames = ["|", "/", "-", "\\"]

    def start(self) -> None:
        if self._thread is not None:
            return

        def _run() -> None:
            idx = 0
            while not self._stop.is_set():
                frame = self._frames[idx % len(self._frames)]
                sys.stderr.write(f"\r{self._message} {frame}")
                sys.stderr.flush()
                idx += 1
                time.sleep(self._interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        # 줄 정리
        sys.stderr.write("\r" + (" " * (len(self._message) + 4)) + "\r")
        sys.stderr.flush()

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.stop()


def run_command(
    cmd: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = 900.0,
    stream_output: bool = False,
    spinner_message: str | None = None,
    show_progress: bool | None = None,
    progress_idle_seconds: float | None = None,
    progress_style: str | None = None,
    progress_interval: float | None = None,
) -> RunResult:
    """
    subprocess 실행 공통 유틸.

    - stream_output=False: stdout/stderr 캡처(기존 동작과 유사), 실패 시 요약 포함
    - stream_output=True : stdout/stderr 를 실시간으로 터미널에 흘린다(진행 상황 확인 용이)
    """
    logger.info("명령 실행: %s", " ".join(cmd))

    # progress 설정(우선순위: 호출 인자 > env > 전역 기본값)
    default_show, default_idle, default_style, default_interval = _get_progress_defaults()
    env_show, env_idle, env_style, env_interval = _progress_settings_from_env()

    effective_show = (
        bool(show_progress)
        if show_progress is not None
        else (env_show if env_show is not None else default_show)
    )
    effective_idle = (
        float(progress_idle_seconds)
        if progress_idle_seconds is not None
        else (env_idle if env_idle is not None else default_idle)
    )
    effective_style = (
        str(progress_style)
        if progress_style is not None
        else (env_style if env_style is not None else default_style)
    )
    effective_interval = (
        float(progress_interval)
        if progress_interval is not None
        else (env_interval if env_interval is not None else default_interval)
    )

    # 메시지가 없으면 커맨드 기반 기본 메시지 생성 (\"모든 단계\" 공통 적용)
    progress_message = spinner_message or _default_progress_message(cmd)
    can_render_progress = bool(effective_show) and _is_tty(sys.stderr)

    if stream_output:
        # gcloud/docker는 stderr로도 진행 로그를 자주 내보내므로 STDOUT으로 합친다.
        try:
            proc = subprocess.Popen(  # noqa: S603
                list(cmd),
                cwd=cwd,
                env=dict(env) if env is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                f"필요한 명령을 찾을 수 없습니다: {cmd[0]} (gcloud/docker 가 설치되어 있는지 확인하세요)"
            ) from e

        out_lines: list[str] = []
        started = time.monotonic()
        deadline = None if timeout is None else started + float(timeout)

        # last activity timestamp shared across threads
        last_activity_lock = threading.Lock()
        last_activity = started

        def _get_last_activity() -> float:
            with last_activity_lock:
                return last_activity

        def _touch_activity() -> None:
            nonlocal last_activity
            with last_activity_lock:
                last_activity = time.monotonic()

        indicator: _IdleProgressIndicator | None = None
        if can_render_progress:
            indicator = _IdleProgressIndicator(
                message=progress_message,
                stream=sys.stderr,
                style=effective_style,
                interval=effective_interval,
                idle_seconds=effective_idle,
            )
            indicator.start(start_time=started, last_activity_getter=_get_last_activity)

        q: queue.Queue[str | None] = queue.Queue()

        def _reader() -> None:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    q.put(line)
            finally:
                q.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            while True:
                now = time.monotonic()
                if deadline is not None and now >= deadline:
                    proc.kill()
                    raise RuntimeError(
                        f"명령 실행이 {timeout}초 안에 끝나지 않았습니다: {' '.join(cmd)}"
                    )

                remaining = None if deadline is None else max(deadline - now, 0.0)
                get_timeout = 0.1 if remaining is None else min(0.1, remaining)

                try:
                    item = q.get(timeout=get_timeout)
                except queue.Empty:
                    if proc.poll() is not None:
                        # reader 종료까지 잠깐 더 기다림
                        try:
                            item = q.get(timeout=0.2)
                        except queue.Empty:
                            break
                    continue

                if item is None:
                    break

                if indicator is not None:
                    indicator.clear()

                out_lines.append(item)
                sys.stdout.write(item)
                sys.stdout.flush()
                _touch_activity()

            reader_thread.join(timeout=1.0)

            wait_timeout = None
            if deadline is not None:
                wait_timeout = max(deadline - time.monotonic(), 0.0)
            returncode = proc.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            raise RuntimeError(
                f"명령 실행이 {timeout}초 안에 끝나지 않았습니다: {' '.join(cmd)}"
            ) from e
        finally:
            try:
                if proc.stdout is not None:
                    proc.stdout.close()
            except Exception:  # noqa: BLE001
                pass
            if indicator is not None:
                indicator.stop()

        if returncode != 0:
            combined = "".join(out_lines).strip()
            detail = "\nstdout/stderr:\n" + shorten(combined, width=2000) if combined else ""
            raise RuntimeError(
                f"명령 실행 실패: {' '.join(cmd)} (exit={returncode}){detail}"
            )

        return RunResult(returncode=returncode, stdout="".join(out_lines), stderr="")

    # capture 모드 (조용히 돌리고 실패 시 요약)
    indicator2: _IdleProgressIndicator | None = None
    started = time.monotonic()
    last_activity_capture = started

    def _get_last_activity_capture() -> float:
        return last_activity_capture

    if can_render_progress:
        indicator2 = _IdleProgressIndicator(
            message=progress_message,
            stream=sys.stderr,
            style=effective_style,
            interval=effective_interval,
            idle_seconds=effective_idle,
        )
        indicator2.start(start_time=started, last_activity_getter=_get_last_activity_capture)

    try:
        result = subprocess.run(
            list(cmd),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=dict(env) if env is not None else None,
        )
        if result.stdout:
            logger.debug("명령 stdout: %s", shorten(result.stdout.strip(), width=2000))
        if result.stderr:
            logger.debug("명령 stderr: %s", shorten(result.stderr.strip(), width=2000))
        return RunResult(returncode=result.returncode, stdout=result.stdout or "", stderr=result.stderr or "")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"필요한 명령을 찾을 수 없습니다: {cmd[0]} (gcloud/docker 가 설치되어 있는지 확인하세요)"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"명령 실행이 {timeout}초 안에 끝나지 않았습니다: {' '.join(cmd)}"
        ) from e
    except subprocess.CalledProcessError as e:
        stdout = (e.stdout or "").strip()
        stderr = (e.stderr or "").strip()
        detail = ""
        if stderr:
            detail = "\nstderr:\n" + shorten(stderr, width=2000)
        elif stdout:
            detail = "\nstdout:\n" + shorten(stdout, width=2000)
        raise RuntimeError(
            f"명령 실행 실패: {' '.join(cmd)} (exit={e.returncode}){detail}"
        ) from e
    finally:
        if indicator2 is not None:
            indicator2.stop()

