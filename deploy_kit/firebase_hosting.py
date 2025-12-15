"""
firebase_hosting
----------------

Firebase Hosting 배포를 담당하는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def deploy_frontend(cfg: DeployConfig, build_dir: str = "dist") -> None:
    """
    프론트엔드 빌드 결과를 Firebase Hosting 으로 배포한다.
    """
    if not (cfg.enable_firebase and cfg.deploy_frontend):
        logger.debug("ENABLE_FIREBASE=false 이거나 DEPLOY_FRONTEND=false 이므로 Firebase 배포를 건너뜁니다.")
        return

    logger.info(
        "Firebase Hosting 배포 (가상): project=%s site=%s dir=%s",
        cfg.firebase_project_id,
        cfg.firebase_hosting_site,
        build_dir,
    )
    # TODO: firebase-tools CLI 를 서브프로세스로 호출


