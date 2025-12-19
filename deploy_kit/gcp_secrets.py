"""
gcp_secrets
-----------

Secret Manager 에 .env.secrets 내용을 업로드하고,
Cloud Run 서비스/Job에서 사용할 수 있도록 매핑하는 모듈.
"""

from __future__ import annotations

import os
from typing import Dict, List

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def load_local_secrets_file(base_dir: str = ".", filename: str = ".env.secrets") -> Dict[str, str]:
    """
    .env.secrets 파일을 파싱하여 dict 로 반환.
    """
    path = os.path.join(base_dir, filename)
    secrets: Dict[str, str] = {}
    if not os.path.exists(path):
        logger.info(".env.secrets 파일이 없어 Secret 로드를 건너뜁니다: %s", path)
        return secrets

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            secrets[key.strip()] = value.strip()

    return secrets


def ensure_secrets(cfg: DeployConfig, base_dir: str = ".") -> List[str]:
    """
    로컬 .env.secrets 를 읽어서 Secret Manager 에 업로드하고,
    생성/업데이트된 secret 이름 목록을 반환한다.
    """
    if not (cfg.enable_secret_manager and cfg.configure_secrets):
        logger.debug("Secret Manager 설정이 비활성화되어 secrets 단계를 건너뜁니다.")
        return []

    local_secrets = load_local_secrets_file(base_dir)
    if not local_secrets:
        logger.info("업로드할 secret 이 없습니다.")
        return []

    client = secretmanager.SecretManagerServiceClient()
    project_id = cfg.gcp_project_id
    parent = f"projects/{project_id}"

    created_or_updated: List[str] = []
    for key, value in local_secrets.items():
        secret_id = f"{cfg.secret_prefix}{key}" if cfg.secret_prefix else key
        secret_name = f"{parent}/secrets/{secret_id}"

        # Secret 존재 여부 확인 후 없으면 생성
        try:
            client.get_secret(name=secret_name)
            logger.info("기존 Secret 에 새 버전을 추가합니다: %s", secret_name)
        except NotFound:
            logger.info("Secret 이 없어 새로 생성합니다: %s", secret_name)
            client.create_secret(
                parent=parent,
                secret_id=secret_id,
                secret={
                    "replication": {"automatic": {}},
                },
            )

        # 새 버전 추가
        client.add_secret_version(
            parent=secret_name,
            payload={"data": value.encode("utf-8")},
        )
        created_or_updated.append(secret_name)

    return created_or_updated


def check_secrets(cfg: DeployConfig, base_dir: str = ".") -> List[str]:
    """
    .env.secrets 에 정의된 Secret 들이 Secret Manager 에 존재하는지 확인한다.
    (없어도 생성하지 않고, 상태만 리턴)
    """
    if not (cfg.enable_secret_manager and cfg.configure_secrets):
        return ["Secrets: Secret Manager 비활성화 (ENABLE_SECRET_MANAGER/CONFIGURE_SECRETS)"]

    local_secrets = load_local_secrets_file(base_dir)
    if not local_secrets:
        return ["Secrets: .env.secrets 에 정의된 값이 없습니다."]

    client = secretmanager.SecretManagerServiceClient()
    project_id = cfg.gcp_project_id
    parent = f"projects/{project_id}"

    results: List[str] = []
    for key in sorted(local_secrets.keys()):
        secret_id = f"{cfg.secret_prefix}{key}" if cfg.secret_prefix else key
        secret_name = f"{parent}/secrets/{secret_id}"

        try:
            client.get_secret(name=secret_name)
            results.append(f"Secrets: 존재함 ({secret_name})")
        except NotFound:
            results.append(f"Secrets: 없음 (생성이 필요함) ({secret_name})")

    return results


