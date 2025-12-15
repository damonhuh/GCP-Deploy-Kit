"""
gcp_sql
-------

Cloud SQL 인스턴스/DB/유저 및 Cloud Run 연결 설정을 담당하는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def ensure_cloud_sql(cfg: DeployConfig) -> None:
    """
    Cloud SQL 리소스가 준비되어 있는지 확인하고, 필요하다면 생성한다.
    초기 버전에서는 '존재한다고 가정'하는 수준까지 구현.
    """
    if not cfg.enable_cloud_sql:
        logger.debug("ENABLE_CLOUD_SQL=false 로 설정되어 Cloud SQL 설정을 건너뜁니다.")
        return

    logger.info(
        "Cloud SQL 설정 확인: instance=%s db=%s user=%s",
        cfg.cloud_sql_instance_name,
        cfg.cloud_sql_db_name,
        cfg.cloud_sql_user,
    )
    # TODO: sqladmin API 또는 gcloud sql 명령어 래핑


