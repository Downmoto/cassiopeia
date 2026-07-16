import shutil
from collections.abc import Callable
from functools import wraps

import click

from ethos.config import HOME_PATH
from ethos.home import initialise_home
from ethos.onboarding import run_onboarding
from ethos.runtime import run_prompt


def requires_home[**P, R](command: Callable[P, R]) -> Callable[P, R]:
    """Require an initialised ethos home for a command."""

    @wraps(command)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        if not HOME_PATH.is_dir():
            raise click.ClickException(
                "ethos is not initialised. Run [ethos init] first."
            )
        return command(*args, **kwargs)

    return guarded


@click.group()
def main() -> None:
    """agent harness"""


@main.command()
@click.option(
    "-r",
    "--reinitialise",
    is_flag=True,
    help="reinitialise a fresh app dir",
)
def init(reinitialise: bool) -> None:
    """(re)initialise ethos app directory at ~/"""

    try:
        if reinitialise:
            if click.confirm(
                "Are you sure you want to reinitialise ethos?\n"
                f"This will permanently delete {HOME_PATH}"
            ):
                initialise_home(HOME_PATH, reinitialise=True)
                click.echo(f".ethos initialised at: {HOME_PATH}")
            else:
                click.echo("Aborted!")
            return

        initialise_home(HOME_PATH)
        click.echo(f".ethos initialised at: {HOME_PATH}")
    except FileExistsError as error:
        raise click.ClickException(
            f"{error}.\nRun [ethos init --reinitialise] to replace it."
        ) from error


@main.command()
def uninit() -> None:
    """Remove the ethos app directory."""
    if not HOME_PATH.is_dir():
        raise click.ClickException(f"ethos home does not exist at: {HOME_PATH}")

    if click.confirm(
        "Are you sure you want to uninitialise ethos?\n"
        f"This will permanently delete {HOME_PATH}"
    ):
        shutil.rmtree(HOME_PATH)
        click.echo(f".ethos removed from: {HOME_PATH}")
    else:
        click.echo("Aborted!")


@main.command()
@requires_home
def onboard() -> None:
    """Configure the settings required to run ethos."""
    run_onboarding(HOME_PATH)
    click.echo(f"ethos configured at: {HOME_PATH}")


@main.command()
@click.argument("prompt")
@requires_home
def ask(prompt: str) -> None:
    """Send one prompt to the configured model."""
    try:
        click.echo(run_prompt(prompt))
    except Exception as error:
        raise click.ClickException(str(error)) from error


@main.command(hidden=True, add_help_option=False)
def debug() -> None:
    """development manual debug command, end users should not be seeing this"""
    click.echo("DEBUG")


if __name__ == "__main__":
    main()
