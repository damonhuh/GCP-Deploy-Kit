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


def check_cloud_sql(cfg: DeployConfig) -> list[str]:
    """
    Cloud SQL 인스턴스/DB 존재 여부를 간단히 확인한다.
    (gcloud sql 을 사용하며, 실제 생성은 하지 않는다)
    """
    results: list[str] = []

    if not cfg.enable_cloud_sql:
        results.append("Cloud SQL: ENABLE_CLOUD_SQL=false (체크 건너뜀)")
        return results

    if not cfg.cloud_sql_instance_name:
        results.append("Cloud SQL: CLOUD_SQL_INSTANCE_NAME 이 설정되지 않았습니다.")
        return results

    import subprocess

    instance_cmd = [
        "gcloud",
        "sql",
        "instances",
        "describe",
        cfg.cloud_sql_instance_name,
        f"--project={cfg.gcp_project_id}",
        "--quiet",
    ]

    try:
        subprocess.run(
            instance_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        results.append(
            f"Cloud SQL: 인스턴스 존재함 ({cfg.cloud_sql_instance_name})"
        )
    except FileNotFoundError:
        results.append("Cloud SQL: gcloud 명령을 찾을 수 없어 상태 확인 불가")
        return results
    except subprocess.CalledProcessError:
        results.append(
            f"Cloud SQL: 인스턴스 없음 (생성이 필요함) ({cfg.cloud_sql_instance_name})"
        )
        return results

    # DB 이름이 설정된 경우 DB 존재 여부도 확인
    if cfg.cloud_sql_db_name:
        db_cmd = [
            "gcloud",
            "sql",
            "databases",
            "describe",
            cfg.cloud_sql_db_name,
            f"--instance={cfg.cloud_sql_instance_name}",
            f"--project={cfg.gcp_project_id}",
            "--quiet",
        ]
        try:
            subprocess.run(
                db_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            results.append(
                f"Cloud SQL: 데이터베이스 존재함 ({cfg.cloud_sql_db_name})"
            )
        except subprocess.CalledProcessError:
            results.append(
                f"Cloud SQL: 데이터베이스 없음 (생성이 필요함) ({cfg.cloud_sql_db_name})"
            )

    return results


