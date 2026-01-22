# deploy-kit

GCP Cloud Run / Cloud Run Job / Firebase Hosting / BigQuery / Cloud SQL / GCS / Secret Manager 를
환경변수 기반으로 한 번에 배포하기 위한 Python CLI 패키지입니다.

## 설치

### 1) GitHub 레포에서 설치 (권장)

```bash
pip install --upgrade --force-reinstall "git+https://github.com/damonhuh/GCP-Deploy-Kit.git@main#egg=deploy-kit"
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

> 참고: `BACKEND_BUILD_MODE=cloud_build` 를 사용하는 경우, Cloud Build API(`cloudbuild.googleapis.com`)도 필수입니다.\
> `deploy-gcp check` / `deploy-gcp deploy` 단계에서 자동으로 체크/활성화합니다.

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
- `frontend_cloud_run` : 프론트엔드 Cloud Run 서비스 배포 (Firebase 없이 스테이지 구성 가능)
- `firebase` : Firebase Hosting 배포

## env 템플릿 생성

서비스 루트 디렉토리에서:

```bash
deploy-gcp init
```

명령을 실행하면 `env.infra.example`, `env.secrets.example`, `env.services.example`
템플릿이 생성됩니다.

### env 파일 역할

- `.env.infra` : GCP 프로젝트/리전, Cloud Run 서비스 이름, ENABLE_*/DEPLOY_* 토글, Artifact Registry 리포/이미지 설정 등
- `.env.secrets` : Secret Manager 로 올라갈 민감한 값(DB 비밀번호, API 키 등)
- `.env.services` : Cloud Run 서비스 내부에서 사용할 일반적인 앱 환경변수
인프라/배포 토글(`GCP_PROJECT_ID`, `ENABLE_*`, `DEPLOY_*` 등)은
`.env.infra` / `.env.secrets` 에 두고,
`.env.services` 에는 애플리케이션 런타임 설정만 두는 것을 권장합니다.

### 주요 env 키 예시(.env.infra)

- `FRONTEND_SOURCE_DIR` / `FRONTEND_BUILD_DIR` : 프론트엔드 소스 디렉토리와 빌드 산출물 디렉토리(`firebase.json` 의 `public` 값과 일치해야 함)
- `CLI_STREAM_SUBPROCESS_OUTPUT` : gcloud/docker/npm 출력 스트리밍 여부. `true`이면 긴 작업에서 진행 로그가 그대로 보여 “멈춘 것 같은” 느낌이 줄어듭니다.
- `CLOUD_BUILD_TIMEOUT_SECONDS` : `BACKEND_BUILD_MODE=cloud_build` 시 Cloud Build 자체 timeout(초). (`gcloud builds submit --timeout=<seconds>s` 로 전달)
- `BACKEND_BUILD_SUBPROCESS_TIMEOUT_SECONDS` : 로컬 CLI가 빌드/푸시/프론트엔드 빌드를 기다리는 최대 시간(초). Cloud Build가 느리면 크게 설정하세요.
- `GCLOUD_RUN_DEPLOY_TIMEOUT_SECONDS` : `gcloud run deploy` 대기 시간(초).
- `BACKEND_IMAGE_PACKAGE` / `ETL_IMAGE_PACKAGE` : Artifact Registry 리포지토리 내에서 backend/etl 이미지가 사용할 패키지명(기본은 각각 `backend`, `etl`)
- `BACKEND_API_HOST` : 프론트엔드 빌드 시 백엔드 API base URL 로 사용할 값.\
  `deploy-gcp deploy --only frontend` 를 실행할 때, `.env.infra` 에 정의한 `FRONTEND_BUILD_COMMAND` 를 실행하며,\
  이때 `BACKEND_API_HOST` 가 설정되어 있으면 `VITE_API_URL` 환경변수로 함께 전달됩니다.
- `FIREBASE_PROJECT_ID` / `FIREBASE_HOSTING_SITE` : Firebase Hosting 배포용 프로젝트/사이트 설정.\
  `FIREBASE_HOSTING_SITE` 는 전체 URL이 아니라 **Hosting 사이트 ID** 여야 합니다.\
  예) 사이트 URL 이 `https://poly-read-aloud.web.app` 인 경우\
  `FIREBASE_PROJECT_ID=vm-deploy-poc`, `FIREBASE_HOSTING_SITE=poly-read-aloud` 로 설정하면,\
  실제 접속 URL 은 `https://poly-read-aloud.web.app` 가 됩니다.
- `FIREBASE_API_PREFIX` : (선택) Firebase Hosting 에서 특정 경로를 Cloud Run 백엔드로 라우팅하고 싶을 때 사용합니다.\
  예) `FIREBASE_API_PREFIX=/api` 로 설정하면, firebase.json 이 없을 경우 deploy-kit 이 다음과 같은 기본 구성을 생성합니다:

  ```json
  {
    "hosting": {
      "public": "dist",
      "rewrites": [
        {
          "source": "/api/**",
          "run": {
            "serviceId": "<BACKEND_SERVICE_NAME>",
            "region": "<GCP_REGION>"
          }
        }
      ]
    }
  }
  ```

  이때 프론트엔드 코드는 `fetch(\"/api/v1/auth/login\")` 처럼 상대 경로만 사용하고,\
  Hosting 도메인(`/api/**`)으로 들어온 요청은 같은 프로젝트의 Cloud Run 백엔드로 전달됩니다.

### 프론트엔드 빌드 연동 예시(Vite)

`.env.infra` 예시:

```bash
FRONTEND_SOURCE_DIR=frontend
BACKEND_API_HOST=https://your-cloud-run-backend-url
FRONTEND_BUILD_COMMAND="npm run build"
```

로컬/CI 에서:

```bash
deploy-gcp deploy --only frontend,firebase
```

- `frontend` 섹션에서 `FRONTEND_SOURCE_DIR`(여기서는 `frontend`) 디렉토리에서 `FRONTEND_BUILD_COMMAND` 에 정의한 빌드 명령(예: `npm run build`)을 실행합니다.
- 이때 `.env.infra` 의 `BACKEND_API_HOST` 값이 `VITE_API_URL` 환경변수로 주입되므로,\
  Vite 프로젝트에서는 `import.meta.env.VITE_API_URL` 을 통해 해당 값을 사용할 수 있습니다.

## 스테이지: Backend + Frontend Cloud Run (Firebase 없이)

Firebase Hosting 도메인을 쓰지 않고, **백엔드/프론트 2개의 Cloud Run 서비스**로 스테이징 환경을 구성할 수 있습니다.

`.env.infra` 예시:

```bash
DEPLOY_BACKEND=true
DEPLOY_FRONTEND_CLOUD_RUN=true

BACKEND_SERVICE_NAME=your-backend-service-name
FRONTEND_SERVICE_NAME=your-frontend-service-name

BACKEND_SOURCE_DIR=backend
FRONTEND_SOURCE_DIR=frontend

BACKEND_IMAGE_NAME=backend
FRONTEND_IMAGE_NAME=frontend
```

배포:

```bash
deploy-gcp deploy --only backend,frontend_cloud_run
```

### (선택) `/api/*` 프록시 라우팅

Firebase Hosting 의 rewrite 처럼, 프론트에서 `/api/*` 를 백엔드로 보내고 싶다면 다음 env 를 사용하세요:

- `FRONTEND_API_PREFIX=/api`
- `FRONTEND_API_TARGET` 또는 `BACKEND_API_HOST` 중 하나

> 참고: Cloud Run 자체에는 rewrite/proxy 기능이 없어서, 실제 reverse proxy 는 프론트 컨테이너(Nginx/Caddy 등)에서 처리해야 합니다. deploy-kit은 위 값을 **Cloud Run env 로 주입**만 합니다.

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

## 패키지 삭제

```bash
pip uninstall deploy-kit
```