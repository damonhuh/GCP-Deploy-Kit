"""
gcp_bq
------

BigQuery 데이터셋 및 권한 설정을 담당하는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def ensure_bigquery_resources(cfg: DeployConfig) -> None:
    """
    BigQuery 프로젝트/데이터셋 존재 여부를 확인하고,
    필요 시 생성한다.
    """
    if not cfg.enable_bigquery:
        logger.debug("ENABLE_BIGQUERY=false 로 설정되어 BigQuery 설정을 건너뜁니다.")
        return

    logger.info(
        "BigQuery 설정 확인: project=%s dataset=%s",
        cfg.bigquery_project_id,
        cfg.bigquery_dataset_id,
    )
    # TODO: google-cloud-bigquery 클라이언트 사용하여 dataset create


