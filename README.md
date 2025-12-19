# deploy-kit

GCP Cloud Run / Cloud Run Job / Firebase Hosting / BigQuery / Cloud SQL / GCS / Secret Manager 를
환경변수 기반으로 한 번에 배포하기 위한 Python CLI 패키지입니다.

## 설치

### 1) GitHub 레포에서 설치 (권장)

```bash
pip install "git+https://github.com/damonhuh/GCP-Deploy-Kit.git@v1.0.0#egg=deploy-kit"
```

### 2) 로컬 editable 설치 (개발용)

프로젝트 루트에서:

```bash
pip install -e ".[dev]"
```

테스트 실행:

```bash
pytest
```

## Quickstart (Cloud Run 백엔드만)

1. 작업 디렉토리(예: 서비스 루트)에 `.env.infra`, `.env.secrets`, `.env.services` 파일을 준비합니다.
2. 다음 명령으로 현재 설정을 점검합니다.

```bash
deploy-gcp plan
deploy-gcp plan -a  # infra/secrets/services 에서 설정한 모든 키/값까지 보고 싶을 때
```

3. 실제 배포를 수행합니다.

```bash
deploy-gcp deploy
```

## 배포 전 사전 체크

아래 명령으로 프로젝트/필수 API/GCS 버킷/BigQuery 데이터셋/Cloud SQL/Secret Manager 상태를
한 번에 점검할 수 있습니다. (실제 리소스 생성/변경은 하지 않습니다.)

```bash
deploy-gcp check
```

섹션별로 제한해서 배포하고 싶다면 (고급 옵션):

```bash
deploy-gcp deploy --only backend,etl
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
deploy-gcp init
```

명령을 실행하면 `env.infra.example`, `env.secrets.example`, `env.services.example`
템플릿이 생성됩니다.

### env 파일 역할

- `.env.infra` : GCP 프로젝트/리전, Cloud Run 서비스 이름, ENABLE_*/DEPLOY_* 토글 등
- `.env.secrets` : Secret Manager 로 올라갈 민감한 값(DB 비밀번호, API 키 등)
- `.env.services` : Cloud Run 서비스 내부에서 사용할 일반적인 앱 환경변수

인프라/배포 토글(`GCP_PROJECT_ID`, `ENABLE_*`, `DEPLOY_*` 등)은
`.env.infra` / `.env.secrets` 에 두고,
`.env.services` 에는 애플리케이션 런타임 설정만 두는 것을 권장합니다.
