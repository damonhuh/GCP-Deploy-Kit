from dataclasses import replace

import pytest

from deploy_kit.config import DeployConfig
from deploy_kit import orchestrator


def _minimal_cfg() -> DeployConfig:
    return DeployConfig(
        gcp_project_id="test-project",
        gcp_region="us-central1",
        deploy_sa_email="sa@test-project.iam.gserviceaccount.com",
        artifact_registry_repo="apps",
        backend_service_name="backend",
    )


def test_apply_all_success_backend_only(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _minimal_cfg()

    # backend_image_name 가 없으면 build/push 를 건너뛰게 된다.
    cfg = replace(cfg, backend_image_name=None)

    monkeypatch.setattr(orchestrator.gcp_auth, "ensure_deploy_service_account", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_auth, "ensure_iam_roles", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_project, "ensure_project_and_apis", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_artifact_registry, "ensure_repository", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_cloud_run, "deploy_backend_service", lambda cfg, image: None)  # type: ignore[arg-type]

    summary, has_failures = orchestrator.apply_all(cfg)

    assert not has_failures
    assert "Executed sections" in summary
    assert "- backend" in summary


def test_apply_all_marks_failed_section(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _minimal_cfg()

    def failing_ensure_project(_cfg: DeployConfig) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(
        orchestrator.gcp_project,
        "ensure_project_and_apis",
        failing_ensure_project,
    )
    monkeypatch.setattr(orchestrator.gcp_auth, "ensure_deploy_service_account", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_auth, "ensure_iam_roles", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_artifact_registry, "ensure_repository", lambda cfg: None)  # type: ignore[arg-type]
    monkeypatch.setattr(orchestrator.gcp_cloud_run, "deploy_backend_service", lambda cfg, image: None)  # type: ignore[arg-type]

    summary, has_failures = orchestrator.apply_all(cfg)

    assert has_failures
    assert "Failed sections" in summary
    assert "- backend" in summary


