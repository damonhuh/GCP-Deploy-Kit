# deploy-kit

GCP Cloud Run / Cloud Run Job / Firebase Hosting / BigQuery / Cloud SQL / GCS / Secret Manager 를
환경변수 기반으로 한 번에 배포하기 위한 Python CLI 패키지입니다.

## 설치 (로컬 개발)

프로젝트 루트에서:

```bash
cd deploy-kit
pip install -e .
```

## 기본 사용법

1. 작업 디렉토리(예: 서비스 루트)에 `.env.infra`, `.env.secrets` 파일을 준비합니다.
2. 다음 명령으로 현재 설정을 점검합니다.

```bash
deploy-main -C /path/to/service plan
```

3. 실제 배포를 수행합니다.

```bash
deploy-main -C /path/to/service apply
```

섹션별로 제한해서 배포하고 싶다면:

```bash
deploy-main -C /path/to/service apply --only backend,etl
```

가능한 섹션 이름:

- `backend` : Cloud Run 백엔드 서비스
- `etl` : Cloud Run Job (ETL)
- `bq` : BigQuery
- `sql` : Cloud SQL
- `gcs` : GCS 버킷
- `secrets` : Secret Manager
- `frontend` : 프론트엔드 빌드 (실제 빌드 스크립트는 서비스별로 연결)
- `firebase` : Firebase Hosting 배포

## env 템플릿 생성

서비스 루트 디렉토리에서:

```bash
deploy-main -C . init
```

명령을 실행하면 `env.infra.example`, `env.secrets.example` 템플릿이 생성됩니다.

## Read_aloud_POC 에서의 사용 시나리오 (예시)

루트 기준:

- 백엔드 소스: `app/Backend`
- 프론트엔드 소스: `app/Frontend`
- ETL Job: `ETL`

### 1) 백엔드 + 프론트 + Secret Manager 만 배포

1. 루트에 `.env.infra`, `.env.secrets` 작성
2. 다음 명령 실행:

```bash
deploy-main -C . plan
deploy-main -C . apply --only backend,secrets,frontend,firebase
```

### 2) ETL Cloud Run Job 만 배포

```bash
DEPLOY_BACKEND=false
DEPLOY_ETL_JOB=true

deploy-main -C . apply --only etl
```



