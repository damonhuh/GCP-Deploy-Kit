import sys
from typing import Optional

import click

from .config import load_env_files, DeployConfig
from .logging_utils import setup_logging, get_logger
from .orchestrator import apply_all, plan_all


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
    ctx.ensure_object(dict)
    ctx.obj["chdir"] = chdir
    ctx.obj["verbose"] = verbose


def _load_config_from_ctx(ctx: click.Context) -> DeployConfig:
    base_dir: str = ctx.obj["chdir"]
    load_env_files(base_dir)
    cfg = DeployConfig.from_env()
    logger.debug("Config loaded: %s", cfg)
    return cfg


@main.command()
@click.pass_context
def plan(ctx: click.Context) -> None:
    """현재 환경변수 기반으로 어떤 리소스가 생성/갱신/스킵될지 출력"""
    try:
        cfg = _load_config_from_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        click.echo(f"[ERROR] 설정 로드 실패: {e}", err=True)
        sys.exit(1)

    report = plan_all(cfg)
    click.echo(report)


@main.command()
@click.option(
    "--only",
    "only",
    type=str,
    default="",
    help="쉼표로 구분된 섹션 이름(backend,frontend,etl,bq,sql,gcs,secrets,firebase)",
)
@click.pass_context
def apply(ctx: click.Context, only: str) -> None:
    """리소스를 실제로 생성/업데이트하여 배포"""
    try:
        cfg = _load_config_from_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        click.echo(f"[ERROR] 설정 로드 실패: {e}", err=True)
        sys.exit(1)

    only_list: Optional[list[str]] = None
    if only.strip():
        only_list = [p.strip() for p in only.split(",") if p.strip()]

    try:
        summary = apply_all(cfg, only_sections=only_list)
    except Exception as e:  # noqa: BLE001
        logger.exception("배포 중 오류 발생")
        click.echo(f"[ERROR] 배포 실패: {e}", err=True)
        sys.exit(1)

    click.echo(summary)


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """
    현재 디렉토리에 env 템플릿(.env.infra.example, .env.secrets.example)을 복사하는 초기화.
    """
    import os
    from importlib import resources

    base_dir: str = ctx.obj["chdir"]

    for name in ("env.infra.example", "env.secrets.example"):
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


