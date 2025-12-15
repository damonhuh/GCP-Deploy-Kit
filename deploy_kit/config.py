from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from dotenv import load_dotenv


ENV_FILES_DEFAULT_ORDER = [".env", ".env.infra", ".env.secrets"]


def load_env_files(base_dir: str = ".",
                   files: Optional[List[str]] = None) -> None:
    """
    주어진 디렉토리에서 .env 계열 파일을 순서대로 로드한다.
    후순위 파일이 같은 키를 덮어쓴다.
    """
    order = files or ENV_FILES_DEFAULT_ORDER
    for name in order:
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            load_dotenv(path, override=True)


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y"}


@dataclass
class DeployConfig:
    # 필수 공통
    gcp_project_id: str
    gcp_region: str
    deploy_sa_email: str
    artifact_registry_repo: str

    backend_image_name: Optional[str] = None
    frontend_image_name: Optional[str] = None

    # 토글
    enable_bigquery: bool = False
    enable_cloud_sql: bool = False
    enable_gcs: bool = False
    enable_firebase: bool = False
    enable_secret_manager: bool = True

    # 부분 배포
    deploy_backend: bool = True
    deploy_frontend: bool = True
    deploy_etl_job: bool = False
    configure_secrets: bool = True

    # 선택 설정들
    bigquery_project_id: Optional[str] = None
    bigquery_dataset_id: Optional[str] = None

    cloud_sql_instance_name: Optional[str] = None
    cloud_sql_db_name: Optional[str] = None
    cloud_sql_user: Optional[str] = None

    gcs_bucket_name: Optional[str] = None
    gcs_prefix: Optional[str] = None

    firebase_project_id: Optional[str] = None
    firebase_hosting_site: Optional[str] = None

    secret_prefix: str = ""

    @classmethod
    def from_env(cls) -> "DeployConfig":
        # 필수값
        missing: List[str] = []
        def req(name: str) -> str:
            val = os.getenv(name)
            if not val:
                missing.append(name)
            return val or ""

        cfg = cls(
            gcp_project_id=req("GCP_PROJECT_ID"),
            gcp_region=req("GCP_REGION"),
            deploy_sa_email=req("DEPLOY_SERVICE_ACCOUNT_EMAIL"),
            artifact_registry_repo=req("ARTIFACT_REGISTRY_REPO"),
            backend_image_name=os.getenv("BACKEND_IMAGE_NAME"),
            frontend_image_name=os.getenv("FRONTEND_IMAGE_NAME"),
            enable_bigquery=_get_bool("ENABLE_BIGQUERY", False),
            enable_cloud_sql=_get_bool("ENABLE_CLOUD_SQL", False),
            enable_gcs=_get_bool("ENABLE_GCS", False),
            enable_firebase=_get_bool("ENABLE_FIREBASE", False),
            enable_secret_manager=_get_bool("ENABLE_SECRET_MANAGER", True),
            deploy_backend=_get_bool("DEPLOY_BACKEND", True),
            deploy_frontend=_get_bool("DEPLOY_FRONTEND", True),
            deploy_etl_job=_get_bool("DEPLOY_ETL_JOB", False),
            configure_secrets=_get_bool("CONFIGURE_SECRETS", True),
            bigquery_project_id=os.getenv("BIGQUERY_PROJECT_ID"),
            bigquery_dataset_id=os.getenv("BIGQUERY_DATASET_ID"),
            cloud_sql_instance_name=os.getenv("CLOUD_SQL_INSTANCE_NAME"),
            cloud_sql_db_name=os.getenv("CLOUD_SQL_DB_NAME"),
            cloud_sql_user=os.getenv("CLOUD_SQL_USER"),
            gcs_bucket_name=os.getenv("GCS_BUCKET_NAME"),
            gcs_prefix=os.getenv("GCS_PREFIX"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID"),
            firebase_hosting_site=os.getenv("FIREBASE_HOSTING_SITE"),
            secret_prefix=os.getenv("SECRET_PREFIX", ""),
        )

        if missing:
            raise ValueError(
                "필수 환경변수가 누락되었습니다: " + ", ".join(sorted(set(missing)))
            )

        # BigQuery 기본값 보정
        if cfg.enable_bigquery and not cfg.bigquery_project_id:
            cfg.bigquery_project_id = cfg.gcp_project_id

        return cfg


