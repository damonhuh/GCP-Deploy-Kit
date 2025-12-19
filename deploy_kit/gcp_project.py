"""
gcp_project
-----------

GCP 프로젝트 존재 여부와 필수 API enable 을 담당하는 모듈.
"""

from __future__ import annotations

import subprocess
from textwrap import shorten

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


def _run_gcloud(cmd: list[str]) -> None:
    """
    gcloud services enable 래퍼.
    """
    logger.info("명령 실행: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.debug(
                "gcloud services stdout: %s",
                shorten(result.stdout.strip(), width=2000),
            )
        if result.stderr:
            logger.debug(
                "gcloud services stderr: %s",
                shorten(result.stderr.strip(), width=2000),
            )
    except FileNotFoundError as e:
        raise RuntimeError(
            "gcloud 명령을 찾을 수 없습니다. gcloud CLI 가 설치/초기화되어 있는지 확인하세요."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        detail = ""
        if stderr:
            detail = "\nstderr:\n" + shorten(stderr, width=2000)
        raise RuntimeError(
            f"필수 API 활성화에 실패했습니다 (exit={e.returncode}).{detail}"
        ) from e


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

    if not unique_apis:
        return

    cmd = [
        "gcloud",
        "services",
        "enable",
        *unique_apis,
        f"--project={cfg.gcp_project_id}",
        "--quiet",
    ]
    _run_gcloud(cmd)


def check_project_and_apis(cfg: DeployConfig) -> list[str]:
    """
    프로젝트와 필수 API 가 이미 활성화되어 있는지 확인한다.
    실제 enable 은 수행하지 않는다.
    """
    results: list[str] = []

    # 프로젝트 존재 여부
    describe_cmd = [
        "gcloud",
        "projects",
        "describe",
        cfg.gcp_project_id,
        "--quiet",
    ]
    logger.info("프로젝트 존재 여부 확인: %s", cfg.gcp_project_id)
    try:
        subprocess.run(
            describe_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        results.append(f"Project: 존재함 ({cfg.gcp_project_id})")
    except FileNotFoundError:
        results.append("Project: gcloud 명령을 찾을 수 없어 확인 불가")
        return results
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip() if e.stderr else ""
        if "NOT_FOUND" in stderr or "not found" in stderr.lower():
            results.append(f"Project: 없음 (생성이 필요함) ({cfg.gcp_project_id})")
        else:
            results.append(
                f"Project: 조회 실패 (gcloud projects describe, exit={e.returncode})"
            )
        return results

    # API 상태 확인
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
    if not unique_apis:
        results.append("APIs: 추가로 필요한 API 없음")
        return results

    for api in unique_apis:
        cmd = [
            "gcloud",
            "services",
            "list",
            "--enabled",
            f"--project={cfg.gcp_project_id}",
            f"--filter=name:{api}",
            "--format=value(config.name)",
            "--quiet",
        ]
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            results.append(f"API: gcloud 명령을 찾을 수 없어 {api} 상태 확인 불가")
            continue

        enabled = bool(proc.stdout.strip())
        if enabled:
            results.append(f"API: 활성화됨 ({api})")
        else:
            results.append(f"API: 비활성화 (enable 필요) ({api})")

    return results


