# deploy-kit

GCP Cloud Run / Cloud Run Job / Firebase Hosting / BigQuery / Cloud SQL / GCS / Secret Manager 를
환경변수 기반으로 한 번에 배포하기 위한 Python CLI 패키지입니다.

## 설치

### 1) GitHub 레포에서 설치 (권장)

```bash
pip install "git+https://github.com/damonhuh/GCP-Deploy-Kit.git@alpha#egg=deploy-kit"
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

## 가장 빠른 시작

1. 서비스 루트 디렉토리(예: 백엔드 프로젝트 루트)에서 env 템플릿을 생성합니다.

```bash
deploy-gcp init
```

`env.infra.example`, `env.secrets.example`, `env.services.example` 템플릿이 생성됩니다.

2. 각 템플릿을 복사/이름을 변경해 실제 env 파일을 만듭니다.

```bash
cp env.infra.example .env.infra
cp env.secrets.example .env.secrets
cp env.services.example .env.services
```

3. `.env.infra`, `.env.secrets`, `.env.services` 내용을 프로젝트에 맞게 수정합니다.
4. 배포 전에 설정/리소스를 한 번 점검합니다.

```bash
deploy-gcp check
```

5. 현재 설정을 요약해서 확인하고,

```bash
deploy-gcp plan
deploy-gcp plan -a  # infra/secrets/services 에서 설정한 모든 키/값까지 보고 싶을 때
```

6. 실제 배포를 수행합니다.

```bash
deploy-gcp deploy
```

## Quickstart (Cloud Run 백엔드만)

- 위의 "가장 빠른 시작" 흐름을 따른 뒤, Cloud Run 백엔드 관련 섹션만 집중해서 배포하고 싶을 때 사용할 수 있는 옵션들입니다.

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

## env 파일과 git (보안)

- `deploy-gcp init` 으로 생성한 `.env.infra`, `.env.secrets`, `.env.services` 에는 **프로덕션 자격 증명/비밀번호/API 키** 가 들어갈 수 있습니다.
- 이 파일들은 절대 원격 git 레포지토리에 커밋되면 안 됩니다.
- `deploy-gcp init` 은 작업 디렉토리의 `.gitignore` 를 생성/갱신하여, 위 3개 파일이 자동으로 git 에서 무시되도록 시도합니다.
- 만약 과거에 이미 커밋해 버렸다면, 아래처럼 한 번 인덱스에서 제거해 주세요.

```bash
git rm --cached .env.infra .env.secrets .env.services
git commit -m "Remove local env files from git tracking"
```

이후에는 `.gitignore` 규칙에 의해 새로 변경된 값들이 git 에 다시 잡히지 않습니다.
