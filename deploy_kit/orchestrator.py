from __future__ import annotations

from typing import Iterable, List, Optional

from .config import DeployConfig
from .logging_utils import get_logger
from . import gcp_auth, gcp_project, gcp_artifact_registry, gcp_cloud_run, gcp_bq, gcp_sql, gcp_gcs, gcp_secrets, firebase_hosting


logger = get_logger(__name__)


def _section_enabled(name: str, cfg: DeployConfig) -> bool:
    if name == "backend":
        return cfg.deploy_backend
    if name == "frontend":
        return cfg.deploy_frontend
    if name == "etl":
        return cfg.deploy_etl_job
    if name == "bq":
        return cfg.enable_bigquery
    if name == "sql":
        return cfg.enable_cloud_sql
    if name == "gcs":
        return cfg.enable_gcs
    if name == "firebase":
        return cfg.enable_firebase and cfg.deploy_frontend
    if name == "secrets":
        return cfg.enable_secret_manager and cfg.configure_secrets
    return False


def _filter_sections(cfg: DeployConfig, only_sections: Optional[Iterable[str]]) -> List[str]:
    all_sections = ["backend", "etl", "bq", "sql", "gcs", "secrets", "frontend", "firebase"]
    if only_sections:
        requested = {s for s in only_sections}
        return [s for s in all_sections if s in requested and _section_enabled(s, cfg)]
    return [s for s in all_sections if _section_enabled(s, cfg)]


def plan_all(cfg: DeployConfig) -> str:
    """
    어떤 섹션이 활성화/비활성화 되는지 요약 텍스트를 리턴.
    실제 GCP 호출은 하지 않는다.
    """
    lines: List[str] = []
    lines.append("# Deploy plan")
    lines.append(f"- project: {cfg.gcp_project_id}")
    lines.append(f"- region: {cfg.gcp_region}")
    lines.append("")

    for name in ["backend", "etl", "bq", "sql", "gcs", "secrets", "frontend", "firebase"]:
        enabled = _section_enabled(name, cfg)
        status = "ENABLED" if enabled else "SKIPPED"
        lines.append(f"- {name}: {status}")

    return "\n".join(lines)


def apply_all(cfg: DeployConfig, only_sections: Optional[Iterable[str]] = None) -> str:
    """
    섹션별로 실제 배포 로직을 호출한다.
    아직은 각 섹션 구현이 비어 있으므로, 함수 골격만 두고
    이후 gcp_* 모듈이 구현되면 연결한다.
    """
    executed: List[str] = []
    skipped: List[str] = []

    sections = _filter_sections(cfg, only_sections)

    logger.info("적용 대상 섹션: %s", sections)

    for name in ["backend", "etl", "bq", "sql", "gcs", "secrets", "frontend", "firebase"]:
        if name not in sections:
            skipped.append(name)
            continue

        logger.info("섹션 실행: %s", name)

        if name == "backend":
            # 공통 인프라 준비
            gcp_auth.ensure_deploy_service_account(cfg)
            gcp_auth.ensure_iam_roles(cfg)
            gcp_project.ensure_project_and_apis(cfg)
            gcp_artifact_registry.ensure_repository(cfg)
            # 이미지 빌드/푸시 및 배포
            if cfg.backend_image_name:
                image_url = gcp_artifact_registry.build_and_push_image(
                    cfg, service="backend", image_name=cfg.backend_image_name
                )
                gcp_cloud_run.deploy_backend_service(cfg, image_url)
        elif name == "etl":
            gcp_project.ensure_project_and_apis(cfg)
            gcp_artifact_registry.ensure_repository(cfg)
            if cfg.backend_image_name:
                image_url = gcp_artifact_registry.build_and_push_image(
                    cfg, service="etl", image_name=cfg.backend_image_name
                )
                gcp_cloud_run.deploy_etl_job(cfg, image_url)
        elif name == "bq":
            gcp_project.ensure_project_and_apis(cfg)
            gcp_bq.ensure_bigquery_resources(cfg)
        elif name == "sql":
            gcp_project.ensure_project_and_apis(cfg)
            gcp_sql.ensure_cloud_sql(cfg)
        elif name == "gcs":
            gcp_project.ensure_project_and_apis(cfg)
            gcp_gcs.ensure_gcs_bucket(cfg)
        elif name == "secrets":
            gcp_project.ensure_project_and_apis(cfg)
            gcp_secrets.ensure_secrets(cfg)
        elif name == "frontend":
            # 실제 Firebase 배포는 firebase 섹션에서 처리,
            # 여기서는 빌드만 담당한다고 가정 가능 (추후 확장)
            logger.info("프론트엔드 빌드를 수행해야 합니다. (프로젝트별 스크립트로 연동)")
        elif name == "firebase":
            firebase_hosting.deploy_frontend(cfg)

        executed.append(name)

    lines: List[str] = []
    lines.append("# Deploy summary")
    lines.append(f"- project: {cfg.gcp_project_id}")
    lines.append("")
    lines.append("## Executed sections")
    if executed:
        for s in executed:
            lines.append(f"- {s}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Skipped sections")
    if skipped:
        for s in skipped:
            lines.append(f"- {s}")
    else:
        lines.append("- (none)")

    return "\n".join(lines)


