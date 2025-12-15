"""
gcp_artifact_registry
---------------------

Artifact Registry 리포지토리 존재 여부 확인 및
이미지 빌드/푸시를 담당하는 모듈.
"""

from __future__ import annotations

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def ensure_repository(cfg: DeployConfig) -> None:
    """
    Artifact Registry 리포가 존재하는지 확인하고,
    없으면 생성한다.
    """
    logger.info("Artifact Registry 리포 확인: %s", cfg.artifact_registry_repo)
    # TODO: gcloud artifacts repositories describe / create


def build_and_push_image(cfg: DeployConfig, service: str, image_name: str, context_dir: str = ".") -> str:
    """
    로컬에서 도커 이미지를 빌드하고 Artifact Registry 에 푸시한 뒤,
    최종 이미지 URL 을 반환한다.

    현재는 실제 구현 대신, 태그 규칙만 정의한다.
    """
    image_url = f"{cfg.gcp_region}-docker.pkg.dev/{cfg.gcp_project_id}/{cfg.artifact_registry_repo}/{service}:latest"
    logger.info("이미지 빌드/푸시 (가상): %s -> %s", image_name, image_url)
    # TODO: docker build / docker push or gcloud builds submit
    return image_url


