from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from dotenv import load_dotenv, dotenv_values


ENV_FILES_DEFAULT_ORDER = [".env", ".env.infra", ".env.services", ".env.secrets"]

# .env.services 에서 읽어온 "서비스용" 환경변수들을 보관하는 전역 변수
_SERVICE_ENV: dict[str, str] = {}


def load_env_files(
    base_dir: str = ".",
    files: Optional[List[str]] = None,
) -> None:
    """
    주어진 디렉토리에서 .env 계열 파일을 순서대로 로드한다.
    후순위 파일이 같은 키를 덮어쓴다.

    .env.services 는 Cloud Run 서비스 내부에서 사용할 일반적인 앱 환경변수용 파일이고,
    인프라/토글 설정(GCP_PROJECT_ID, ENABLE_*, DEPLOY_* 등)은
    .env.infra / .env.secrets 에 두는 것을 권장한다.
    """
    global _SERVICE_ENV

    order = files or ENV_FILES_DEFAULT_ORDER
    for name in order:
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            # .env.services 는 Cloud Run 서비스용 env 로도 따로 보관
            if name == ".env.services":
                raw = dotenv_values(path)
                # 값이 None 인 항목은 제외
                _SERVICE_ENV = {k: v for k, v in raw.items() if v is not None}
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

    # Cloud Run 서비스 이름
    backend_service_name: str

    # 이미지 빌드 전략 (local_docker | cloud_build)
    backend_build_mode: str = "local_docker"

    # Cloud Run 공개 여부
    backend_allow_unauthenticated: bool = True

    backend_image_name: Optional[str] = None
    frontend_image_name: Optional[str] = None
    # Artifact Registry 리포지토리 내 이미지 패키지명(옵션, 미설정 시 service 이름 사용)
    backend_image_package: Optional[str] = None
    etl_image_package: Optional[str] = None
    # 프론트엔드 빌드 시 백엔드 API base URL 로 사용할 값 (예: BACKEND_API_HOST=https://...run.app)
    backend_api_host: Optional[str] = None

    # 소스 코드 경로
    # - BACKEND_SOURCE_DIR: 백엔드(및 ETL) Docker 빌드 컨텍스트 디렉토리
    # - FRONTEND_SOURCE_DIR: 프론트엔드 빌드 디렉토리 (선택)
    backend_source_dir: str = "."
    frontend_source_dir: Optional[str] = None
    # 프론트엔드 빌드 산출물 디렉토리 (firebase.json 의 public 과 일치해야 함)
    frontend_build_dir: str = "dist"

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
    # Firebase Hosting 에서 /api 등의 경로를 Cloud Run 백엔드로 rewrite 하고 싶을 때 사용하는 prefix
    # 예) FIREBASE_API_PREFIX=/api  → /api/** 가 Cloud Run backend 로 라우팅
    firebase_api_prefix: Optional[str] = None

    secret_prefix: str = ""

    # Cloud Run 서비스 내부 환경변수 (key/value 쌍)
    backend_service_env: dict[str, str] | None = None

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
            backend_service_name=req("BACKEND_SERVICE_NAME"),
            backend_build_mode=os.getenv("BACKEND_BUILD_MODE", "local_docker"),
            backend_allow_unauthenticated=_get_bool(
                "BACKEND_ALLOW_UNAUTHENTICATED", True
            ),
            backend_image_name=os.getenv("BACKEND_IMAGE_NAME"),
            frontend_image_name=os.getenv("FRONTEND_IMAGE_NAME"),
            backend_image_package=os.getenv("BACKEND_IMAGE_PACKAGE"),
            etl_image_package=os.getenv("ETL_IMAGE_PACKAGE"),
            backend_api_host=os.getenv("BACKEND_API_HOST"),
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
            firebase_api_prefix=os.getenv("FIREBASE_API_PREFIX"),
            secret_prefix=os.getenv("SECRET_PREFIX", ""),
            backend_source_dir=os.getenv("BACKEND_SOURCE_DIR", "."),
            frontend_source_dir=os.getenv("FRONTEND_SOURCE_DIR"),
            frontend_build_dir=os.getenv("FRONTEND_BUILD_DIR", "dist"),
            # .env.services 에서 읽어온 값들만 Cloud Run 서비스 env 로 전달
            backend_service_env=dict(_SERVICE_ENV),
        )

        if missing:
            raise ValueError(
                "필수 환경변수가 누락되었습니다: " + ", ".join(sorted(set(missing)))
            )

        # 기능 토글별 추가 검증
        errors: List[str] = []

        # BigQuery 기본값/검증
        if cfg.enable_bigquery:
            if not cfg.bigquery_project_id:
                cfg.bigquery_project_id = cfg.gcp_project_id
            if not cfg.bigquery_dataset_id:
                errors.append(
                    "ENABLE_BIGQUERY=true 이면 BIGQUERY_DATASET_ID 환경변수가 필요합니다."
                )

        # Cloud SQL
        if cfg.enable_cloud_sql:
            if not cfg.cloud_sql_instance_name:
                errors.append(
                    "ENABLE_CLOUD_SQL=true 이면 CLOUD_SQL_INSTANCE_NAME 환경변수가 필요합니다."
                )
            if not cfg.cloud_sql_db_name:
                errors.append(
                    "ENABLE_CLOUD_SQL=true 이면 CLOUD_SQL_DB_NAME 환경변수가 필요합니다."
                )
            if not cfg.cloud_sql_user:
                errors.append(
                    "ENABLE_CLOUD_SQL=true 이면 CLOUD_SQL_USER 환경변수가 필요합니다."
                )

        # GCS
        if cfg.enable_gcs and not cfg.gcs_bucket_name:
            errors.append(
                "ENABLE_GCS=true 이면 GCS_BUCKET_NAME 환경변수가 필요합니다."
            )

        # Firebase Hosting
        if cfg.enable_firebase:
            if not cfg.firebase_project_id:
                errors.append(
                    "ENABLE_FIREBASE=true 이면 FIREBASE_PROJECT_ID 환경변수가 필요합니다."
                )
            if not cfg.firebase_hosting_site:
                errors.append(
                    "ENABLE_FIREBASE=true 이면 FIREBASE_HOSTING_SITE 환경변수가 필요합니다."
                )

        if errors:
            raise ValueError(
                "환경변수 설정이 잘못되었습니다:\n- " + "\n- ".join(errors)
            )

        return cfg


