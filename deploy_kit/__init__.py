"""
deploy_kit
-----------

GCP용 범용 배포 CLI 패키지.
Cloud Run 서비스, Cloud Run Job, Firebase Hosting, BigQuery, Cloud SQL,
GCS, Secret Manager 등을 환경변수 기반으로 설정하고 한 번에 배포하는 것을 목표로 한다.
"""

__all__ = [
    "config",
    "orchestrator",
]


