import os

import pytest

from deploy_kit.config import DeployConfig


def _base_env() -> dict[str, str]:
    return {
        "GCP_PROJECT_ID": "test-project",
        "GCP_REGION": "us-central1",
        "DEPLOY_SERVICE_ACCOUNT_EMAIL": "sa@test-project.iam.gserviceaccount.com",
        "ARTIFACT_REGISTRY_REPO": "apps",
        "BACKEND_SERVICE_NAME": "backend",
    }


def test_missing_required_env_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = _base_env()

    # 필수 값 중 GCP_PROJECT_ID 만 비워둔다.
    for key, value in env.items():
        if key == "GCP_PROJECT_ID":
            continue
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    with pytest.raises(ValueError) as excinfo:
        DeployConfig.from_env()

    assert "GCP_PROJECT_ID" in str(excinfo.value)


def test_bigquery_toggle_requires_dataset_id(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env()
    env.update(
        {
            "ENABLE_BIGQUERY": "true",
            # BIGQUERY_DATASET_ID intentionally omitted
        }
    )

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValueError) as excinfo:
        DeployConfig.from_env()

    assert "BIGQUERY_DATASET_ID" in str(excinfo.value)


