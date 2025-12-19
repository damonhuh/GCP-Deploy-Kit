from typing import List

from deploy_kit.config import DeployConfig
from deploy_kit import gcp_artifact_registry as ar


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

    def fake_run(cmd: list[str], *, timeout: float = 900.0) -> None:  # noqa: ARG001
        calls.append(cmd)

    monkeypatch.setattr(ar, "_run", fake_run)

    cfg = _cfg("local_docker")
    image_url = ar.build_and_push_image(cfg, service="backend", image_name="backend")

    assert image_url.startswith("us-central1-docker.pkg.dev/test-project/apps/backend")
    # docker build + docker push 두 번 호출되는지 확인
    assert len(calls) == 2
    assert calls[0][0] == "docker"
    assert calls[1][0] == "docker"


