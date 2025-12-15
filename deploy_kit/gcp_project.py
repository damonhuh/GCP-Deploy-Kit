"""
gcp_project
-----------

GCP 프로젝트 존재 여부와 필수 API enable 을 담당하는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


REQUIRED_APIS_BASE = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
]

REQUIRED_APIS_BQ = ["bigquery.googleapis.com"]
REQUIRED_APIS_SQL = ["sqladmin.googleapis.com"]
REQUIRED_APIS_GCS = ["storage.googleapis.com"]
REQUIRED_APIS_FIREBASE = ["firebase.googleapis.com", "firebaserules.googleapis.com"]


def ensure_project_and_apis(cfg: DeployConfig) -> None:
    """
    프로젝트가 존재한다고 가정하고,
    필요한 API 들이 enable 되어 있는지 확인/enable 한다.
    """
    logger.info("프로젝트 및 API 설정 확인: %s", cfg.gcp_project_id)

    apis = list(REQUIRED_APIS_BASE)
    if cfg.enable_bigquery:
        apis += REQUIRED_APIS_BQ
    if cfg.enable_cloud_sql:
        apis += REQUIRED_APIS_SQL
    if cfg.enable_gcs:
        apis += REQUIRED_APIS_GCS
    if cfg.enable_firebase:
        apis += REQUIRED_APIS_FIREBASE

    unique_apis = sorted(set(apis))
    logger.info("다음 API 들이 활성화되어 있어야 합니다: %s", unique_apis)
    # TODO: gcloud services enable 호출 래핑


