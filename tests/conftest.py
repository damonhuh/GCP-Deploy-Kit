"""
pytest 설정:

로컬 작업 환경에 설치된 다른 버전의 deploy_kit 패키지가 존재할 때,
`pytest` 실행 시 site-packages 쪽이 먼저 import 되어 테스트가 깨질 수 있다.

테스트는 항상 현재 레포의 소스를 대상으로 해야 하므로, repo root 를 sys.path 최상단에 고정한다.
"""

from __future__ import annotations

import os
import sys


def pytest_configure() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

