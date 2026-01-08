import os
import sys
from typing import Optional

import click
from dotenv import dotenv_values

from .config import load_env_files, DeployConfig
from .logging_utils import setup_logging, get_logger
from .orchestrator import ALL_SECTIONS, apply_all, plan_all, check_all


logger = get_logger(__name__)


@click.group()
@click.option(
    "-C",
    "--chdir",
    "chdir",
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    default=".",
    help="작업 디렉토리 (기본: 현재 디렉토리)",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="로그 레벨을 DEBUG로 올립니다. (-v 가 많을수록 더 자세한 로그)",
)
@click.pass_context
def main(ctx: click.Context, chdir: str, verbose: int) -> None:
    """GCP Cloud Run / Firebase / Cloud Run Job 배포용 CLI"""
    setup_logging(verbose)
    # 작업 디렉토리를 실제로 변경하여 firebase.json 등 상대 경로 기준을 명확히 맞춘다.
    try:
        os.chdir(chdir)
    except OSError as e:  # noqa: BLE001
        # click 이 이미 존재 여부를 검증했으므로, 여기서 예외가 나면 치명적인 오류로 간주한다.
        logger.exception("작업 디렉토리 변경에 실패했습니다: %s", e)
        click.echo(f"[ERROR] 작업 디렉토리 변경 실패: {e}", err=True)
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj["chdir"] = chdir
    ctx.obj["verbose"] = verbose


def _load_config_from_ctx(ctx: click.Context) -> DeployConfig:
    base_dir: str = ctx.obj["chdir"]
    load_env_files(base_dir)
    cfg = DeployConfig.from_env()
    logger.debug("Config loaded: %s", cfg)
    return cfg


def _build_env_dump(base_dir: str) -> str:
    """
    .env.infra / .env.secrets / .env.services 의 내용을 그대로 덤프한다.
    (주석/빈 줄은 제외)
    """
    lines: list[str] = []
    for filename in (".env.infra", ".env.secrets", ".env.services"):
        lines.append(f"## {filename}")
        path_values = dotenv_values(dotenv_path=f"{base_dir}/{filename}")
        if not path_values:
            lines.append("- (파일이 없거나 비어 있습니다)")
        else:
            for k, v in sorted(path_values.items()):
                # None 은 dotenv 에서 값이 없는 키를 의미하므로 스킵
                if v is None:
                    continue
                lines.append(f"- {k}={v}")
        lines.append("")
    return "\n".join(lines).rstrip()  # 마지막 공백 줄 제거


@main.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="infra/secrets/services 에서 설정한 모든 환경설정을 함께 출력합니다.",
)
@click.pass_context
def plan(ctx: click.Context, show_all: bool) -> None:
    """현재 설정(.env.infra/.env.secrets/.env.services)을 요약 및 섹션별 ENABLED/SKIPPED 상태로 출력"""
    try:
        cfg = _load_config_from_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        click.echo(f"[ERROR] 설정 로드 실패: {e}", err=True)
        sys.exit(1)

    report = plan_all(cfg)

    if show_all:
        base_dir: str = ctx.obj["chdir"]
        env_dump = _build_env_dump(base_dir)
        report = report + "\n\n" + "## Raw env from files\n" + env_dump

    click.echo(report)


@main.command(name="deploy")
@click.option(
    "--only",
    "only",
    type=str,
    default="",
    help="쉼표로 구분된 섹션 이름(backend,frontend,etl,bq,sql,gcs,secrets,firebase). "
    "기본 동작은 .env.infra 의 ENABLE_*/DEPLOY_* 토글을 사용합니다.",
)
@click.pass_context
def deploy(ctx: click.Context, only: str) -> None:
    """리소스를 실제로 생성/업데이트하여 배포"""
    try:
        cfg = _load_config_from_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        click.echo(f"[ERROR] 설정 로드 실패: {e}", err=True)
        sys.exit(1)

    only_list: Optional[list[str]] = None
    if only.strip():
        only_list = [p.strip() for p in only.split(",") if p.strip()]

        # --only 섹션 이름 검증
        invalid = sorted({s for s in only_list if s not in ALL_SECTIONS})
        if invalid:
            click.echo(
                "[ERROR] 잘못된 섹션 이름이 있습니다: "
                + ", ".join(invalid)
                + f"\n허용되는 섹션: {', '.join(ALL_SECTIONS)}",
                err=True,
            )
            sys.exit(1)

    try:
        summary, has_failures = apply_all(cfg, only_sections=only_list)
    except Exception as e:  # noqa: BLE001
        logger.exception("배포 중 오류 발생")
        click.echo(f"[ERROR] 배포 실패: {e}", err=True)
        sys.exit(1)

    click.echo(summary)

    # 섹션 단위 실패가 있었다면 전체 명령은 실패(exit 1)로 간주
    if has_failures:
        sys.exit(1)


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """
    현재 디렉토리에 env 템플릿(.env.infra.example, .env.secrets.example, .env.services.example)을 복사하고,
    .env.infra / .env.secrets / .env.services 가 git 에서 무시되도록 .gitignore 를 생성/갱신합니다.
    """
    import os
    from importlib import resources

    base_dir: str = ctx.obj["chdir"]

    # 1) env 템플릿 파일 복사
    for name in ("env.infra.example", "env.secrets.example", "env.services.example"):
        target = os.path.join(base_dir, name)
        if os.path.exists(target):
            click.echo(f"{name} 이(가) 이미 존재하여 건너뜀")
            continue
        try:
            with resources.files("deploy_kit.examples").joinpath(name).open("r", encoding="utf-8") as src, open(
                target, "w", encoding="utf-8"
            ) as dst:
                dst.write(src.read())
            click.echo(f"{name} 템플릿을 생성했습니다.")
        except FileNotFoundError:
            click.echo(f"템플릿 {name} 을(를) 패키지에서 찾을 수 없습니다.", err=True)

    # 2) .gitignore 에 실제 env 파일(.env.infra/.env.secrets/.env.services)을 무시하도록 규칙 추가/유지
    gitignore_path = os.path.join(base_dir, ".gitignore")
    patterns = [".env.infra", ".env.secrets", ".env.services"]

    existing_content = ""
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        except OSError:
            # .gitignore 를 읽을 수 없으면 조용히 건너뛰되, init 자체는 성공 처리
            return

    lines = existing_content.splitlines() if existing_content else []
    missing = [p for p in patterns if p not in lines]

    if not existing_content or missing:
        # 중복 없이 패턴을 추가하기 위해 기존 내용 뒤에 블록을 덧붙인다.
        block_lines: list[str] = []
        if existing_content and not existing_content.endswith("\n"):
            existing_content = existing_content + "\n"
        # 섹션 주석
        block_lines.append("")
        block_lines.append("# deploy-gcp: ignore local env files")
        # 이미 있는 패턴은 제외하고, 없는 패턴만 추가
        for p in patterns:
            if p not in lines:
                block_lines.append(p)

        new_content = existing_content + "\n".join(block_lines) + "\n"

        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            click.echo(
                "[deploy-gcp] .gitignore 에 .env.infra/.env.secrets/.env.services 무시 규칙을 추가/유지했습니다."
            )
        except OSError:
            # .gitignore 를 쓸 수 없더라도 init 자체는 성공으로 간주
            return


@main.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="모든 체크 항목의 상세 상태를 출력합니다. (기본은 이슈만 요약)",
)
@click.pass_context
def check(ctx: click.Context, show_all: bool) -> None:
    """
    최종 배포 전에 GCP 리소스/환경설정 상태를 점검한다.
    (실제 리소스 생성/변경은 하지 않는다)
    """
    try:
        cfg = _load_config_from_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        click.echo(f"[ERROR] 설정 로드 실패: {e}", err=True)
        sys.exit(1)

    base_dir: str = ctx.obj["chdir"]

    try:
        report, has_issues = check_all(cfg, base_dir=base_dir, show_all=show_all)
    except Exception as e:  # noqa: BLE001
        logger.exception("사전 체크 중 오류 발생")
        click.echo(f"[ERROR] 체크 실패: {e}", err=True)
        sys.exit(1)

    click.echo(report)

    # 치명적인 이슈가 있으면 exit 1 로 종료하여 CI 등에서 감지 가능하게 한다.
    if has_issues:
        sys.exit(1)

