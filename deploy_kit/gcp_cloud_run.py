"""
gcp_cloud_run
-------------

Cloud Run 서비스 및 Cloud Run Job 배포 책임을 가지는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def deploy_backend_service(cfg: DeployConfig, image_url: str) -> None:
    """
    백엔드 Cloud Run 서비스를 배포한다.
    """
    logger.info("Cloud Run 백엔드 서비스 배포 (가상): image=%s", image_url)
    # TODO: gcloud run deploy 래핑


def deploy_etl_job(cfg: DeployConfig, image_url: str) -> None:
    """
    ETL 용 Cloud Run Job 을 배포한다.
    """
    logger.info("Cloud Run Job 배포 (가상): image=%s", image_url)
    # TODO: gcloud run jobs deploy 래핑


