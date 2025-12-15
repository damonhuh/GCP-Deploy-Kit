"""
gcp_gcs
-------

GCS 버킷 및 prefix 구성을 담당하는 모듈.
"""

from __future__ import annotations

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

    logger.info("GCS 버킷 확인: %s (prefix=%s)", cfg.gcs_bucket_name, cfg.gcs_prefix)
    # TODO: google-cloud-storage 클라이언트 사용하여 bucket create


