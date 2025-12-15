"""
gcp_auth
--------

여기서는 gcloud/ADC 상태를 확인하고,
배포용 서비스 계정 및 역할을 준비하는 유틸을 정의한다.

초기 버전에서는 실제 구현을 최소화하고,
추후 점진적으로 flesh-out 할 수 있도록 골격만 제공한다.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def ensure_deploy_service_account(cfg: DeployConfig) -> None:
    """
    배포에 사용할 서비스 계정이 존재하는지 확인하고,
    없다면 생성 + 기본 권한을 부여한다.

    현재는 gcloud CLI를 직접 호출하지 않고,
    '여기서 처리해야 한다'는 책임만 명확히 남겨둔다.
    """
    logger.info("배포 서비스 계정 확인: %s", cfg.deploy_sa_email)
    # TODO: gcloud iam service-accounts describe / create 래핑 구현


def ensure_iam_roles(cfg: DeployConfig) -> None:
    """
    배포용 서비스 계정 및 런타임 서비스 계정에 필요한
    IAM 역할을 부여하는 책임을 가진다.
    """
    logger.info("필요 IAM 역할을 점검합니다. (실제 부여 로직은 추후 구현)")
    # TODO: roles/run.admin, roles/artifactregistry.admin, ...


