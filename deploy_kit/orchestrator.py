from __future__ import annotations

from typing import Iterable, List, Optional

from .config import DeployConfig
from .logging_utils import get_logger
from . import (
    gcp_auth,
    gcp_project,
    gcp_artifact_registry,
    gcp_cloud_run,
    gcp_bq,
    gcp_sql,
    gcp_gcs,
    gcp_secrets,
    firebase_hosting,
)


logger = get_logger(__name__)

# CLI 등에서 사용할 수 있도록 섹션 이름을 상수로 노출
ALL_SECTIONS: List[str] = [
    "backend",
    "etl",
    "bq",
    "sql",
    "gcs",
    "secrets",
    "frontend",
    "firebase",
]


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
    """
    토글/only_sections 에 따라 실제 실행 대상 섹션 목록을 결정한다.
    """
    if only_sections:
        requested = {s for s in only_sections}
        return [s for s in ALL_SECTIONS if s in requested and _section_enabled(s, cfg)]
    return [s for s in ALL_SECTIONS if _section_enabled(s, cfg)]


def plan_all(cfg: DeployConfig) -> str:
    """
    현재 설정된 옵션 및 어떤 섹션이 활성화/비활성화 되는지
    요약 텍스트를 리턴한다. 실제 GCP 호출은 하지 않는다.
    """
    lines: List[str] = []
    lines.append("# Deploy plan")
    lines.append(f"- project: {cfg.gcp_project_id}")
    lines.append(f"- region: {cfg.gcp_region}")
    lines.append("")

    # 주요 설정 요약
    lines.append("## Config summary")
    lines.append(f"- backend_source_dir: {cfg.backend_source_dir}")
    lines.append(
        f"- frontend_source_dir: {cfg.frontend_source_dir or '(not set)'}",
    )
    lines.append(f"- enable_bigquery: {cfg.enable_bigquery}")
    lines.append(f"- enable_cloud_sql: {cfg.enable_cloud_sql}")
    lines.append(f"- enable_gcs: {cfg.enable_gcs}")
    lines.append(f"- enable_firebase: {cfg.enable_firebase}")
    lines.append(f"- enable_secret_manager: {cfg.enable_secret_manager}")
    lines.append(f"- deploy_backend: {cfg.deploy_backend}")
    lines.append(f"- deploy_frontend: {cfg.deploy_frontend}")
    lines.append(f"- deploy_etl_job: {cfg.deploy_etl_job}")
    lines.append(f"- configure_secrets: {cfg.configure_secrets}")
    lines.append("")

    lines.append("## Sections")

    for name in ALL_SECTIONS:
        enabled = _section_enabled(name, cfg)
        status = "ENABLED" if enabled else "SKIPPED"
        lines.append(f"- {name}: {status}")

    return "\n".join(lines)


def apply_all(cfg: DeployConfig, only_sections: Optional[Iterable[str]] = None) -> tuple[str, bool]:
    """
    섹션별로 실제 배포 로직을 호출한다.

    Returns:
        summary: 사람이 읽기 좋은 텍스트 요약
        has_failures: 하나 이상의 섹션에서 예외가 발생했는지 여부
    """
    executed: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []

    sections = _filter_sections(cfg, only_sections)

    logger.info("적용 대상 섹션: %s", sections)

    for name in ALL_SECTIONS:
        if name not in sections:
            skipped.append(name)
            continue

        logger.info("섹션 실행: %s", name)

        try:
            if name == "backend":
                # 공통 인프라 준비
                gcp_auth.ensure_deploy_service_account(cfg)
                gcp_auth.ensure_iam_roles(cfg)
                gcp_project.ensure_project_and_apis(cfg)
                gcp_artifact_registry.ensure_repository(cfg)
                # 이미지 빌드/푸시 및 배포
                if cfg.backend_image_name:
                    image_url = gcp_artifact_registry.build_and_push_image(
                        cfg,
                        service="backend",
                        image_name=cfg.backend_image_name,
                        context_dir=cfg.backend_source_dir,
                    )
                    gcp_cloud_run.deploy_backend_service(cfg, image_url)
            elif name == "etl":
                gcp_project.ensure_project_and_apis(cfg)
                gcp_artifact_registry.ensure_repository(cfg)
                if cfg.backend_image_name:
                    image_url = gcp_artifact_registry.build_and_push_image(
                        cfg,
                        service="etl",
                        image_name=cfg.backend_image_name,
                        context_dir=cfg.backend_source_dir,
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
                logger.info(
                    "프론트엔드 빌드를 수행해야 합니다. (프로젝트별 스크립트로 연동)"
                )
            elif name == "firebase":
                firebase_hosting.deploy_frontend(cfg)
        except Exception:  # noqa: BLE001
            failed.append(name)
            logger.exception("섹션 실행 실패: %s", name)
            continue

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

    lines.append("")
    lines.append("## Failed sections")
    if failed:
        for s in failed:
            lines.append(f"- {s}")
    else:
        lines.append("- (none)")

    summary = "\n".join(lines)
    return summary, bool(failed)


def check_all(cfg: DeployConfig, base_dir: str = ".", show_all: bool = False) -> tuple[str, bool]:
    """
    실제 리소스 생성 없이, 현재 설정과 GCP 리소스 상태를 종합적으로 점검한다.

    Returns:
        summary: 사람이 읽기 좋은 텍스트 요약
        has_issues: 치명적인 이슈(프로젝트 없음, 필수 자원 없음 등)가 있는지 여부
    """
    lines: List[str] = []
    critical: List[str] = []
    warnings: List[str] = []

    lines.append("# Deploy pre-check")
    lines.append(f"- project: {cfg.gcp_project_id}")
    lines.append(f"- region: {cfg.gcp_region}")
    lines.append("")

    # 1) 프로젝트 및 API
    lines.append("## Project & APIs")
    try:
        project_results = gcp_project.check_project_and_apis(cfg)
        for r in project_results:
            if show_all:
                lines.append(f"- {r}")
            # 프로젝트 없음/확인 불가/조회 실패는 크리티컬
            if "Project: 없음" in r or "확인 불가" in r or "조회 실패" in r:
                critical.append(r)
            # API 비활성화는 우리 패키지가 enable 할 수 있으므로 워닝
            elif "API: 비활성화" in r:
                warnings.append(r)
    except Exception as e:  # noqa: BLE001
        msg = f"Project/APIs: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 2) Artifact Registry
    lines.append("## Artifact Registry")
    try:
        ar_status = gcp_artifact_registry.check_repository(cfg)
        if show_all:
            lines.append(f"- {ar_status}")
        # 리포 없으면 우리 패키지가 생성 가능 → 경고
        if "리포지토리 없음" in ar_status:
            warnings.append(ar_status)
        # 상태 확인 불가 등은 크리티컬
        elif "확인 불가" in ar_status or "실패" in ar_status:
            critical.append(ar_status)
    except Exception as e:  # noqa: BLE001
        msg = f"Artifact Registry: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 3) GCS
    lines.append("## GCS")
    try:
        gcs_status = gcp_gcs.check_gcs_bucket(cfg)
        if show_all:
            lines.append(f"- {gcs_status}")
        # ENABLE_GCS=false 인 경우는 정보성이라 별도 이슈로 보지 않는다.
        if "GCS_BUCKET_NAME 이 설정되지 않았습니다" in gcs_status:
            critical.append(gcs_status)
        elif "버킷 없음" in gcs_status:
            # 우리 패키지가 생성할 수 있는 리소스 → 경고
            warnings.append(gcs_status)
    except Exception as e:  # noqa: BLE001
        msg = f"GCS: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 4) BigQuery
    lines.append("## BigQuery")
    try:
        bq_status = gcp_bq.check_bigquery_resources(cfg)
        if show_all:
            lines.append(f"- {bq_status}")
        if "BIGQUERY_DATASET_ID 가 설정되지 않았습니다" in bq_status:
            critical.append(bq_status)
        elif "데이터셋 없음" in bq_status:
            # 우리 패키지가 생성할 수 있는 리소스 → 경고
            warnings.append(bq_status)
    except Exception as e:  # noqa: BLE001
        msg = f"BigQuery: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 5) Cloud SQL
    lines.append("## Cloud SQL")
    try:
        sql_results = gcp_sql.check_cloud_sql(cfg)
        for r in sql_results:
            if show_all:
                lines.append(f"- {r}")
            # Cloud SQL 은 현재 우리 패키지가 리소스를 생성하지 않으므로,
            # 인스턴스/DB 없음이나 설정 누락을 크리티컬로 본다.
            if "없음" in r or "설정되지 않았습니다" in r or "확인 불가" in r:
                critical.append(r)
    except Exception as e:  # noqa: BLE001
        msg = f"Cloud SQL: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 6) Secrets
    lines.append("## Secret Manager")
    try:
        secret_results = gcp_secrets.check_secrets(cfg, base_dir=base_dir)
        for r in secret_results:
            if show_all:
                lines.append(f"- {r}")
            # Secret 은 우리 패키지가 생성 가능한 리소스이므로, 존재하지 않으면 경고
            if "없음" in r:
                warnings.append(r)
    except Exception as e:  # noqa: BLE001
        msg = f"Secrets: 체크 중 예외 발생: {e}"
        if show_all:
            lines.append(f"- {msg}")
        critical.append(msg)

    lines.append("")

    # 7) 섹션 활성 상태 요약 (show_all 일 때만 자세히 출력)
    if show_all:
        lines.append("## Section toggles")
        for name in ALL_SECTIONS:
            enabled = _section_enabled(name, cfg)
            status = "ENABLED" if enabled else "SKIPPED"
            lines.append(f"- {name}: {status}")
        lines.append("")

    # Summary
    lines.append("## Summary")
    if critical:
        lines.append("- 상태: 크리티컬 이슈가 있습니다. 배포 전 반드시 해결해야 합니다.")
    elif warnings:
        lines.append("- 상태: 경고만 있습니다. 배포 시 일부 리소스가 새로 생성됩니다.")
    else:
        lines.append("- 상태: 주요 이슈 없음 (배포 가능 상태로 보입니다)")

    if show_all or critical:
        lines.append("")
        lines.append("### Critical issues")
        if critical:
            for i in critical:
                lines.append(f"- {i}")
        else:
            lines.append("- (none)")

    if show_all or warnings:
        lines.append("")
        lines.append("### Warnings (리소스가 새로 생성될 예정)")
        if warnings:
            for i in warnings:
                lines.append(f"- {i}")
        else:
            lines.append("- (none)")

    if not show_all:
        lines.append("")
        lines.append("자세한 상태를 보려면 `deploy-gcp check -a` 를 실행하세요.")

    summary = "\n".join(lines)
    # 크리티컬/경고 둘 중 하나라도 있으면 has_issues=True
    return summary, bool(critical or warnings)


