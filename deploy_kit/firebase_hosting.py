"""
firebase_hosting
----------------

Firebase Hosting 배포를 담당하는 모듈.
"""

from __future__ import annotations

import subprocess
from textwrap import shorten

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def deploy_frontend(cfg: DeployConfig, build_dir: str = "dist") -> None:
    """
    프론트엔드 빌드 결과를 Firebase Hosting 으로 배포한다.

    build_dir 는 firebase.json / .firebaserc 가 존재하는 디렉토리(또는 그 하위)를
    기준으로 설정해야 한다.
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
            cwd=build_dir,
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
    except FileNotFoundError as e:
        raise RuntimeError(
            "firebase 명령을 찾을 수 없습니다. firebase-tools 가 설치되어 있는지 확인하세요."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        detail = ""
        if stderr:
            detail = "\nstderr:\n" + shorten(stderr, width=2000)
        raise RuntimeError(
            f"Firebase Hosting 배포에 실패했습니다 (exit={e.returncode}).{detail}"
        ) from e


