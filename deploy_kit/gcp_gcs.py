"""
gcp_gcs
-------

GCS 버킷 및 prefix 구성을 담당하는 모듈.
"""

from __future__ import annotations

from google.cloud import storage

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def ensure_gcs_bucket(cfg: DeployConfig) -> None:
    """
    GCS 버킷이 존재하는지 확인하고, 없으면 생성한다.
    """
    if not cfg.enable_gcs:
        logger.debug("ENABLE_GCS=false 로 설정되어 GCS 설정을 건너뜁니다.")
        return

    if not cfg.gcs_bucket_name:
        raise ValueError(
            "ENABLE_GCS=true 이면 GCS_BUCKET_NAME 환경변수가 필요합니다."
        )

    bucket_name = cfg.gcs_bucket_name
    logger.info("GCS 버킷 확인: %s (prefix=%s)", bucket_name, cfg.gcs_prefix)

    client = storage.Client(project=cfg.gcp_project_id)
    bucket = client.bucket(bucket_name)

    if bucket.exists():
        logger.info("기존 GCS 버킷을 사용합니다: %s", bucket_name)
        return

    bucket.location = cfg.gcp_region
    client.create_bucket(bucket)
    logger.info("GCS 버킷을 생성했습니다: %s (location=%s)", bucket_name, cfg.gcp_region)


def check_gcs_bucket(cfg: DeployConfig) -> str:
    """
    GCS 버킷 존재 여부를 확인만 하고, 생성하지 않는다.
    """
    if not cfg.enable_gcs:
        return "GCS: ENABLE_GCS=false (체크 건너뜀)"

    if not cfg.gcs_bucket_name:
        return "GCS: GCS_BUCKET_NAME 이 설정되지 않았습니다."

    client = storage.Client(project=cfg.gcp_project_id)
    bucket = client.bucket(cfg.gcs_bucket_name)
    exists = bucket.exists()

    if exists:
        return f"GCS: 버킷 존재함 ({cfg.gcs_bucket_name})"
    return f"GCS: 버킷 없음 (생성이 필요함) ({cfg.gcs_bucket_name})"


