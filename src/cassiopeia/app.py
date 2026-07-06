import click

from cassiopeia.home import initialise_home
from cassiopeia.shared import HOME_PATH


@click.group()
def main() -> None:
    """cassieopeia agent harnesss"""


@main.command()
@click.option(
    "-r",
    "--reinitialise",
    is_flag=True,
    help="reinitialise a fresh app dir",
)
def init(reinitialise: bool) -> None:
    """(re)initialise cassiopeia app directory at ~/"""

    try:
        if reinitialise:
            if click.confirm(
                "Are you sure you want to reinitialise cassiopeia?\n"
                f"This will permanently delete {HOME_PATH}"
            ):
                initialise_home(HOME_PATH, reinitialise=True)
                click.echo(f".cassiopeia initialised at: {HOME_PATH}")
            else:
                click.echo("Aborted!")
            return

        initialise_home(HOME_PATH)
        click.echo(f".cassiopeia initialised at: {HOME_PATH}")
    except FileExistsError as error:
        raise click.ClickException(
            f"{error}.\nRun [cass init --reinitialise] to replace it."
        ) from error


if __name__ == "__main__":
    main()
