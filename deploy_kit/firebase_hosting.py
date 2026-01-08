"""
firebase_hosting
----------------

Firebase Hosting 배포를 담당하는 모듈.
"""

from __future__ import annotations

import os
import subprocess
from shutil import which as _which
from textwrap import shorten

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def deploy_frontend(cfg: DeployConfig, build_dir: str | None = None) -> None:
    """
    프론트엔드 빌드 결과를 Firebase Hosting 으로 배포한다.

    build_dir 는 firebase.json / .firebaserc 가 존재하는 디렉토리를 기준으로 한
    프론트엔드 빌드 산출물 디렉토리이다.
    명시되지 않은 경우 cfg.frontend_build_dir (기본 dist)를 사용한다.
    """
    if not (cfg.enable_firebase and cfg.deploy_frontend):
        logger.debug(
            "ENABLE_FIREBASE=false 이거나 DEPLOY_FRONTEND=false 이므로 Firebase 배포를 건너뜁니다."
        )
        return

    if not cfg.firebase_project_id or not cfg.firebase_hosting_site:
        raise ValueError(
            "Firebase 배포를 위해서는 FIREBASE_PROJECT_ID 와 "
            "FIREBASE_HOSTING_SITE 환경변수가 모두 필요합니다."
        )

    # build_dir 가 명시되지 않으면 설정 값(frontend_build_dir)을 사용
    if build_dir is None:
        build_dir = getattr(cfg, "frontend_build_dir", "dist")

    # firebase CLI 존재 여부를 사전에 확인
    if _which("firebase") is None:
        raise RuntimeError(
            "firebase 명령을 찾을 수 없습니다. firebase-tools 가 전역 혹은 현재 환경에 "
            "설치되어 있는지 확인하세요."
        )

    # 프론트엔드 빌드 산출물 디렉토리 존재 여부 확인
    if not os.path.isdir(build_dir):
        raise RuntimeError(
            f"Firebase Hosting 배포용 빌드 디렉토리를 찾을 수 없습니다: {build_dir!r}. "
            "프론트엔드 빌드가 완료되었는지와 FRONTEND_BUILD_DIR 설정을 확인하세요."
        )

    logger.info(
        "Firebase Hosting 배포: project=%s site=%s dir=%s",
        cfg.firebase_project_id,
        cfg.firebase_hosting_site,
        build_dir,
    )

    cmd = [
        "firebase",
        "deploy",
        "--only",
        f"hosting:{cfg.firebase_hosting_site}",
        "--project",
        cfg.firebase_project_id,
        "--non-interactive",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.debug(
                "firebase deploy stdout: %s",
                shorten(result.stdout.strip(), width=2000),
            )
        if result.stderr:
            logger.debug(
                "firebase deploy stderr: %s",
                shorten(result.stderr.strip(), width=2000),
            )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        detail = ""
        if stderr:
            detail = "\nstderr:\n" + shorten(stderr, width=2000)
        raise RuntimeError(
            f"Firebase Hosting 배포에 실패했습니다 (exit={e.returncode}).{detail}"
        ) from e


