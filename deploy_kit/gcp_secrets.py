"""
gcp_secrets
-----------

Secret Manager 에 .env.secrets 내용을 업로드하고,
Cloud Run 서비스/Job에서 사용할 수 있도록 매핑하는 모듈.
"""

from __future__ import annotations

import os
from typing import Dict, List

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

    created_or_updated: List[str] = []
    for key, value in local_secrets.items():
        secret_name = f"{cfg.secret_prefix}{key}" if cfg.secret_prefix else key
        logger.info("Secret 생성/업데이트 (가상): %s", secret_name)
        # TODO: google-cloud-secret-manager 클라이언트 사용하여 secret create / add version
        created_or_updated.append(secret_name)

    return created_or_updated


