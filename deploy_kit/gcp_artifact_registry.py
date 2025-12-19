"""
gcp_artifact_registry
---------------------

Artifact Registry 리포지토리 존재 여부 확인 및
이미지 빌드/푸시를 담당하는 모듈.
"""

from __future__ import annotations

import subprocess
from textwrap import shorten

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def _run(cmd: list[str], *, timeout: float = 900.0) -> None:
    """
    공통 subprocess 실행 헬퍼.

    - stdout/stderr 를 캡처하여 실패 시 일부를 에러 메시지에 포함
    - timeout 초과 시 RuntimeError 로 래핑
    """
    logger.info("명령 실행: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.stdout:
            logger.debug("명령 stdout: %s", shorten(result.stdout.strip(), width=2000))
        if result.stderr:
            logger.debug("명령 stderr: %s", shorten(result.stderr.strip(), width=2000))
    except FileNotFoundError as e:  # gcloud/docker 미설치 등
        raise RuntimeError(
            f"필요한 명령을 찾을 수 없습니다: {cmd[0]} "
            "(gcloud/docker 가 설치되어 있는지 확인하세요)"
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


def ensure_repository(cfg: DeployConfig) -> None:
    """
    Artifact Registry 리포가 존재하는지 확인하고,
    없으면 생성한다.
    """
    logger.info("Artifact Registry 리포 확인: %s", cfg.artifact_registry_repo)
    repo = cfg.artifact_registry_repo
    location = cfg.gcp_region
    project = cfg.gcp_project_id

    # describe 시도
    describe_cmd = [
        "gcloud",
        "artifacts",
        "repositories",
        "describe",
        repo,
        f"--location={location}",
        f"--project={project}",
    ]
    import subprocess

    try:
        _run(describe_cmd)
        logger.info("기존 Artifact Registry 리포를 사용합니다: %s", repo)
        return
    except RuntimeError as e:
        # describe 실패 시에만 create 시도 (다른 오류일 수도 있으므로 로그 남김)
        logger.warning("리포지토리 조회 실패, 생성 시도: %s", e)

    create_cmd = [
        "gcloud",
        "artifacts",
        "repositories",
        "create",
        repo,
        "--repository-format=DOCKER",
        f"--location={location}",
        f"--project={project}",
    ]
    _run(create_cmd)
    logger.info("Artifact Registry 리포를 생성했습니다: %s", repo)


def build_and_push_image(cfg: DeployConfig, service: str, image_name: str, context_dir: str = ".") -> str:
    """
    로컬에서 도커 이미지를 빌드하고 Artifact Registry 에 푸시한 뒤,
    최종 이미지 URL 을 반환한다.

    빌드 방식은 cfg.backend_build_mode 에 따라 동작한다.
    """
    image_url = f"{cfg.gcp_region}-docker.pkg.dev/{cfg.gcp_project_id}/{cfg.artifact_registry_repo}/{service}:latest"

    mode = (cfg.backend_build_mode or "local_docker").lower()
    logger.info("이미지 빌드 모드: %s", mode)

    if mode == "local_docker":
        # 로컬 Docker 사용
        build_cmd = ["docker", "build", "-t", image_url, context_dir]
        push_cmd = ["docker", "push", image_url]
        _run(build_cmd)
        _run(push_cmd)
    elif mode == "cloud_build":
        # Cloud Build 사용 (gcloud builds submit)
        build_cmd = [
            "gcloud",
            "builds",
            "submit",
            context_dir,
            f"--tag={image_url}",
            f"--project={cfg.gcp_project_id}",
        ]
        _run(build_cmd)
    else:
        raise ValueError(f"알 수 없는 BACKEND_BUILD_MODE 값입니다: {cfg.backend_build_mode!r} (local_docker | cloud_build 중 하나)")

    logger.info("이미지 빌드/푸시 완료: %s -> %s", image_name, image_url)
    return image_url


def check_repository(cfg: DeployConfig) -> str:
    """
    Artifact Registry 리포지토리 존재 여부를 확인만 하고, 생성하지 않는다.
    """
    repo = cfg.artifact_registry_repo
    location = cfg.gcp_region
    project = cfg.gcp_project_id

    describe_cmd = [
        "gcloud",
        "artifacts",
        "repositories",
        "describe",
        repo,
        f"--location={location}",
        f"--project={project}",
        "--quiet",
    ]

    try:
        result = subprocess.run(
            describe_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.debug(
                "Artifact Registry describe stdout: %s",
                shorten(result.stdout.strip(), width=2000),
            )
        return f"Artifact Registry: 리포지토리 존재함 ({repo})"
    except FileNotFoundError:
        return "Artifact Registry: gcloud 명령을 찾을 수 없어 상태 확인 불가"
    except subprocess.CalledProcessError:
        return f"Artifact Registry: 리포지토리 없음 (생성이 필요함) ({repo})"



