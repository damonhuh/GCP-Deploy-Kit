"""
gcp_bq
------

BigQuery 데이터셋 및 권한 설정을 담당하는 모듈.
"""

from __future__ import annotations

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

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

    if not cfg.bigquery_dataset_id:
        raise ValueError(
            "ENABLE_BIGQUERY=true 이면 BIGQUERY_DATASET_ID 환경변수가 필요합니다."
        )

    project_id = cfg.bigquery_project_id or cfg.gcp_project_id
    dataset_id = cfg.bigquery_dataset_id
    full_dataset_id = f"{project_id}.{dataset_id}"

    logger.info(
        "BigQuery 설정 확인: project=%s dataset=%s",
        project_id,
        dataset_id,
    )

    client = bigquery.Client(project=project_id)

    try:
        client.get_dataset(full_dataset_id)
        logger.info("기존 BigQuery 데이터셋을 사용합니다: %s", full_dataset_id)
    except NotFound:
        dataset = bigquery.Dataset(full_dataset_id)
        dataset.location = cfg.gcp_region
        client.create_dataset(dataset, exists_ok=True)
        logger.info("BigQuery 데이터셋을 생성했습니다: %s", full_dataset_id)


def check_bigquery_resources(cfg: DeployConfig) -> str:
    """
    BigQuery 데이터셋 존재 여부를 확인만 하고, 생성하지 않는다.
    """
    if not cfg.enable_bigquery:
        return "BigQuery: ENABLE_BIGQUERY=false (체크 건너뜀)"

    if not cfg.bigquery_dataset_id:
        return "BigQuery: BIGQUERY_DATASET_ID 가 설정되지 않았습니다."

    project_id = cfg.bigquery_project_id or cfg.gcp_project_id
    dataset_id = cfg.bigquery_dataset_id
    full_dataset_id = f"{project_id}.{dataset_id}"

    client = bigquery.Client(project=project_id)

    try:
        client.get_dataset(full_dataset_id)
        return f"BigQuery: 데이터셋 존재함 ({full_dataset_id})"
    except NotFound:
        return f"BigQuery: 데이터셋 없음 (생성이 필요함) ({full_dataset_id})"


