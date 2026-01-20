"""
gcp_cloud_run
-------------

Cloud Run 서비스 및 Cloud Run Job 배포 책임을 가지는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger
from .subprocess_utils import run_command


logger = get_logger(__name__)


def _build_backend_env(cfg: DeployConfig) -> dict:
    """
    DeployConfig.backend_service_env 에 담긴 값들에서
    인프라용 키들을 제외하고, Cloud Run 서비스에 전달할 env dict 를 만든다.
    """
    if not cfg.backend_service_env:
        return {}

    # 인프라/토글용으로 사용하는 환경변수 키 목록
    infra_keys = {
        "GCP_PROJECT_ID",
        "GCP_REGION",
        "DEPLOY_SERVICE_ACCOUNT_EMAIL",
        "ARTIFACT_REGISTRY_REPO",
        "BACKEND_SERVICE_NAME",
        "BACKEND_BUILD_MODE",
        "BACKEND_ALLOW_UNAUTHENTICATED",
        "BACKEND_IMAGE_NAME",
        "FRONTEND_IMAGE_NAME",
        "ENABLE_BIGQUERY",
        "ENABLE_CLOUD_SQL",
        "ENABLE_GCS",
        "ENABLE_FIREBASE",
        "ENABLE_SECRET_MANAGER",
        "DEPLOY_BACKEND",
        "DEPLOY_FRONTEND",
        "DEPLOY_ETL_JOB",
        "CONFIGURE_SECRETS",
        "BIGQUERY_PROJECT_ID",
        "BIGQUERY_DATASET_ID",
        "CLOUD_SQL_INSTANCE_NAME",
        "CLOUD_SQL_DB_NAME",
        "CLOUD_SQL_USER",
        "GCS_BUCKET_NAME",
        "GCS_PREFIX",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_HOSTING_SITE",
        "SECRET_PREFIX",
    }

    env: dict[str, str] = {}
    for k, v in cfg.backend_service_env.items():
        if k in infra_keys:
            continue
        # Secret Manager 에서 관리할 민감한 값들은 .env.secrets 쪽으로 보내는 것을 권장.
        env[k] = v
    return env


def _run_gcloud(cfg: DeployConfig, cmd: list[str], *, spinner_message: str) -> None:
    run_command(
        cmd,
        timeout=cfg.gcloud_run_deploy_timeout_seconds,
        stream_output=cfg.cli_stream_subprocess_output,
        spinner_message=None if cfg.cli_stream_subprocess_output else spinner_message,
    )


def deploy_backend_service(cfg: DeployConfig, image_url: str) -> None:
    """
    백엔드 Cloud Run 서비스를 배포한다.
    """
    service_env = _build_backend_env(cfg)
    # 인프라에서 정한 Cloud Run 서비스 이름
    service_name = cfg.backend_service_name

    env_arg = ""
    if service_env:
        pairs = [f"{k}={v}" for k, v in service_env.items()]
        env_arg = ",".join(pairs)

    cmd = [
        "gcloud",
        "run",
        "deploy",
        service_name,
        f"--image={image_url}",
        f"--region={cfg.gcp_region}",
        f"--project={cfg.gcp_project_id}",
        f"--service-account={cfg.deploy_sa_email}",
        "--platform=managed",
        "--quiet",
    ]

    if env_arg:
        cmd.append(f"--set-env-vars={env_arg}")

    if cfg.backend_allow_unauthenticated:
        cmd.append("--allow-unauthenticated")
    else:
        cmd.append("--no-allow-unauthenticated")

    logger.info(
        "Cloud Run 백엔드 서비스 배포: service=%s, image=%s, env_keys=%s, allow_unauth=%s",
        service_name,
        image_url,
        sorted(service_env.keys()),
        cfg.backend_allow_unauthenticated,
    )

    _run_gcloud(cfg, cmd, spinner_message="Cloud Run 서비스 배포 중")


def deploy_etl_job(cfg: DeployConfig, image_url: str) -> None:
    """
    ETL 용 Cloud Run Job 을 배포한다.
    """
    logger.info("Cloud Run Job 배포: image=%s", image_url)

    job_name = f"{cfg.backend_service_name}-etl"
    service_env = _build_backend_env(cfg)

    env_arg = ""
    if service_env:
        pairs = [f"{k}={v}" for k, v in service_env.items()]
        env_arg = ",".join(pairs)

    cmd = [
        "gcloud",
        "run",
        "jobs",
        "deploy",
        job_name,
        f"--image={image_url}",
        f"--region={cfg.gcp_region}",
        f"--project={cfg.gcp_project_id}",
        f"--service-account={cfg.deploy_sa_email}",
        "--platform=managed",
        "--quiet",
    ]

    if env_arg:
        cmd.append(f"--set-env-vars={env_arg}")

    logger.info(
        "Cloud Run Job 배포: job=%s, image=%s, env_keys=%s",
        job_name,
        image_url,
        sorted(service_env.keys()),
    )

    _run_gcloud(cfg, cmd, spinner_message="Cloud Run Job 배포 중")


