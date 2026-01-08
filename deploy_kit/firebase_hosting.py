"""
firebase_hosting
----------------

Firebase Hosting 배포를 담당하는 모듈.
"""

from __future__ import annotations

import json
import os
import subprocess
from shutil import which as _which
from textwrap import shorten
from typing import Any

from .config import DeployConfig
from .logging_utils import get_logger


logger = get_logger(__name__)


def _ensure_firebase_json(cfg: DeployConfig, build_dir: str) -> None:
    """
    현재 작업 디렉토리에 firebase.json 이 없으면,
    기본 Hosting 설정(범용)을 가진 firebase.json 을 생성한다.

    - hosting.site: cfg.firebase_hosting_site (있으면)
    - hosting.public: build_dir
    - hosting.ignore: firebase 권장 기본값
    - hosting.rewrites:
        - cfg.firebase_api_prefix 가 설정된 경우,
          해당 prefix 로 들어오는 요청을 Cloud Run backend 서비스로 라우팅
          (gcp_region / backend_service_name 사용)
        - SPA 라우팅을 위한 fallback (\"**\" → /index.html)
    """
    config_path = os.path.join(os.getcwd(), "firebase.json")
    if os.path.exists(config_path):
        logger.debug("기존 firebase.json 이 존재하므로 새로 생성하지 않습니다: %s", config_path)
        return

    hosting: dict[str, Any] = {
        "public": build_dir,
        "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    }

    if cfg.firebase_hosting_site:
        hosting["site"] = cfg.firebase_hosting_site

    rewrites: list[dict[str, Any]] = []
    api_prefix = (cfg.firebase_api_prefix or "").strip()
    if api_prefix:
        # prefix 가 "/" 로 시작하도록 정규화
        if not api_prefix.startswith("/"):
            api_prefix = "/" + api_prefix
        # trailing slash 제거 후 /** 패턴으로 변환
        source_prefix = api_prefix.rstrip("/")
        rewrites.append(
            {
                "source": f"{source_prefix}/**",
                "run": {
                    "serviceId": cfg.backend_service_name,
                    "region": cfg.gcp_region,
                },
            }
        )

    # SPA 라우팅용 fallback 설정: 나머지 모든 경로는 /index.html 로 전달
    # index.html 이 실제로 존재하지 않아도 Hosting 전체가 깨지지는 않으며,
    # SPA 가 아닌 프로젝트는 firebase.json 을 직접 제공하여 이 구성을 덮어쓸 수 있다.
    rewrites.append(
        {
            "source": "**",
            "destination": "/index.html",
        }
    )

    hosting["rewrites"] = rewrites

    config: dict[str, Any] = {"hosting": hosting}

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("firebase.json 이 없어 기본 구성을 생성했습니다: %s", config_path)
    except OSError as e:  # noqa: BLE001
        logger.warning("firebase.json 생성에 실패했습니다(계속 진행): %s", e)


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

    # firebase.json 이 없다면, 범용적인 기본 구성을 생성한다.
    _ensure_firebase_json(cfg, build_dir)

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


