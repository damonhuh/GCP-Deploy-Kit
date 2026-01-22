"""
gcp_artifact_registry
---------------------

Artifact Registry 리포지토리 존재 여부 확인 및
이미지 빌드/푸시를 담당하는 모듈.
"""

from __future__ import annotations

from textwrap import shorten

from .config import DeployConfig
from .logging_utils import get_logger
from .subprocess_utils import run_command


logger = get_logger(__name__)


def _run(
    cmd: list[str],
    *,
    timeout: float | None = 900.0,
    stream_output: bool = False,
    spinner_message: str | None = None,
) -> None:
    """
    공통 subprocess 실행 헬퍼.

    - stdout/stderr 를 캡처하여 실패 시 일부를 에러 메시지에 포함
    - timeout 초과 시 RuntimeError 로 래핑
    """
    # shorten import는 기존 로그 스타일 유지용(하위 호환)이며,
    # 실제 실행/에러 메시지 포맷팅은 run_command가 담당한다.
    _ = shorten  # noqa: F841
    run_command(
        cmd,
        timeout=timeout,
        stream_output=stream_output,
        spinner_message=spinner_message,
    )


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
        _run(
            describe_cmd,
            timeout=cfg.gcloud_run_deploy_timeout_seconds,
            stream_output=cfg.cli_stream_subprocess_output,
            spinner_message="Artifact Registry 리포 확인 중",
        )
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
    _run(
        create_cmd,
        timeout=cfg.gcloud_run_deploy_timeout_seconds,
        stream_output=cfg.cli_stream_subprocess_output,
        spinner_message="Artifact Registry 리포 생성 중",
    )
    logger.info("Artifact Registry 리포를 생성했습니다: %s", repo)


def build_and_push_image(cfg: DeployConfig, service: str, image_name: str, context_dir: str = ".") -> str:
    """
    로컬에서 도커 이미지를 빌드하고 Artifact Registry 에 푸시한 뒤,
    최종 이미지 URL 을 반환한다.

    빌드 방식은 cfg.backend_build_mode 에 따라 동작한다.

    이미지 경로의 패키지명은 서비스별 설정값이 있을 경우 이를 사용하고,
    없으면 service 인자를 그대로 사용한다.
    """
    # 서비스별 패키지명 선택
    if service == "backend" and cfg.backend_image_package:
        package = cfg.backend_image_package
    elif service == "etl" and cfg.etl_image_package:
        package = cfg.etl_image_package
    elif service == "frontend" and getattr(cfg, "frontend_image_package", None):
        # DeployConfig 에 frontend_image_package 가 없던 구버전과의 호환을 위해 getattr 사용
        package = str(getattr(cfg, "frontend_image_package"))
    else:
        package = service

    image_url = f"{cfg.gcp_region}-docker.pkg.dev/{cfg.gcp_project_id}/{cfg.artifact_registry_repo}/{package}:latest"

    mode = (cfg.backend_build_mode or "local_docker").lower()
    logger.info(
        "이미지 빌드 모드: %s (service=%s, package=%s, logical_name=%s)",
        mode,
        service,
        package,
        image_name,
    )

    if mode == "local_docker":
        # 로컬 Docker 사용
        build_cmd = ["docker", "build", "-t", image_url, context_dir]
        push_cmd = ["docker", "push", image_url]
        _run(
            build_cmd,
            timeout=cfg.backend_build_subprocess_timeout_seconds,
            stream_output=cfg.cli_stream_subprocess_output,
            spinner_message="Docker 이미지 빌드 중",
        )
        _run(
            push_cmd,
            timeout=cfg.backend_build_subprocess_timeout_seconds,
            stream_output=cfg.cli_stream_subprocess_output,
            spinner_message="Docker 이미지 푸시 중",
        )
    elif mode == "cloud_build":
        # Cloud Build 사용 (gcloud builds submit)
        cloud_timeout = max(int(cfg.cloud_build_timeout_seconds), 1)
        build_cmd = [
            "gcloud",
            "builds",
            "submit",
            context_dir,
            f"--tag={image_url}",
            f"--timeout={cloud_timeout}s",
            f"--project={cfg.gcp_project_id}",
        ]
        _run(
            build_cmd,
            timeout=cfg.backend_build_subprocess_timeout_seconds,
            stream_output=cfg.cli_stream_subprocess_output,
            spinner_message="Cloud Build 이미지 빌드 중",
        )
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
        result = run_command(
            describe_cmd,
            timeout=cfg.gcloud_run_deploy_timeout_seconds,
            stream_output=False,
            spinner_message=None,
        )
        if result.stdout:
            logger.debug(
                "Artifact Registry describe stdout: %s",
                shorten(result.stdout.strip(), width=2000),
            )
        return f"Artifact Registry: 리포지토리 존재함 ({repo})"
    except RuntimeError as e:
        msg = str(e)
        if "찾을 수 없습니다" in msg:
            return "Artifact Registry: gcloud 명령을 찾을 수 없어 상태 확인 불가"
        # describe 실패는 보통 리포 없음
        return f"Artifact Registry: 리포지토리 없음 (생성이 필요함) ({repo})"



