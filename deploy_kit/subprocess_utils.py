from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from textwrap import shorten
from typing import Mapping, Sequence

from .logging_utils import get_logger


logger = get_logger(__name__)


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
) -> RunResult:
    """
    subprocess 실행 공통 유틸.

    - stream_output=False: stdout/stderr 캡처(기존 동작과 유사), 실패 시 요약 포함
    - stream_output=True : stdout/stderr 를 실시간으로 터미널에 흘린다(진행 상황 확인 용이)
    """
    logger.info("명령 실행: %s", " ".join(cmd))

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
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                out_lines.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()

            returncode = proc.wait(timeout=timeout)
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

        if returncode != 0:
            combined = "".join(out_lines).strip()
            detail = "\nstdout/stderr:\n" + shorten(combined, width=2000) if combined else ""
            raise RuntimeError(
                f"명령 실행 실패: {' '.join(cmd)} (exit={returncode}){detail}"
            )

        return RunResult(returncode=returncode, stdout="".join(out_lines), stderr="")

    # capture 모드 (조용히 돌리고 실패 시 요약)
    spinner: Spinner | None = None
    if spinner_message:
        spinner = Spinner(spinner_message)
        spinner.start()

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
        if spinner is not None:
            spinner.stop()

