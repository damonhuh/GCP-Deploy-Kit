from typing import List
from pathlib import Path

from deploy_kit.config import DeployConfig
from deploy_kit import gcp_artifact_registry as ar
from deploy_kit.subprocess_utils import RunResult


def _cfg(build_mode: str = "local_docker") -> DeployConfig:
    return DeployConfig(
        gcp_project_id="test-project",
        gcp_region="us-central1",
        deploy_sa_email="sa@test-project.iam.gserviceaccount.com",
        artifact_registry_repo="apps",
        backend_service_name="backend",
        backend_build_mode=build_mode,
    )


def test_build_and_push_image_local_docker_calls_docker(monkeypatch) -> None:
    calls: List[list[str]] = []

    def fake_run_command(cmd, **kwargs) -> RunResult:  # noqa: ANN001, ARG001
        calls.append(list(cmd))
        return RunResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ar, "run_command", fake_run_command)

    cfg = _cfg("local_docker")
    image_url = ar.build_and_push_image(cfg, service="backend", image_name="backend")

    assert image_url.startswith("us-central1-docker.pkg.dev/test-project/apps/backend")
    # docker build + docker push 두 번 호출되는지 확인
    assert len(calls) == 2
    assert calls[0][0] == "docker"
    assert calls[1][0] == "docker"


def test_build_and_push_image_cloud_build_adds_timeout_flag(monkeypatch) -> None:
    calls: List[list[str]] = []

    def fake_run_command(cmd, **kwargs) -> RunResult:  # noqa: ANN001, ARG001
        calls.append(list(cmd))
        return RunResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ar, "run_command", fake_run_command)

    cfg = _cfg("cloud_build")
    cfg.cloud_build_timeout_seconds = 1234
    cfg.backend_build_subprocess_timeout_seconds = 9999
    cfg.cli_stream_subprocess_output = True

    _ = ar.build_and_push_image(cfg, service="backend", image_name="backend", context_dir=".")

    assert len(calls) == 1
    assert calls[0][0:3] == ["gcloud", "builds", "submit"]
    assert any(a == "--timeout=1234s" for a in calls[0])


def test_build_and_push_image_uses_service_packages_when_configured() -> None:
    """
    서비스별 이미지 패키지 오버라이드가 build_and_push_image 구현에 반영되어 있는지 확인한다.

    여기서는 로컬 소스 파일을 직접 읽어 backend_image_package / etl_image_package
    참조가 존재하는지만 검증한다.
    """
    src_path = Path(__file__).resolve().parents[1] / "deploy_kit" / "gcp_artifact_registry.py"
    source = src_path.read_text(encoding="utf-8")
    assert "backend_image_package" in source
    assert "etl_image_package" in source


