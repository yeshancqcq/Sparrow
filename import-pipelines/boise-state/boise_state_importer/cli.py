from os import environ
from click import command, option, echo, secho, style
from pathlib import Path
from sparrow import Database
from sparrow.import_helpers import SparrowImportError, working_directory, iterfiles
from .import_datafile import import_datafile

@command()
def cli(stop_on_error=False, verbose=False):
    """
    Import Boise State XML files
    """
    varname = "SPARROW_DATA_DIR"
    env = environ.get(varname, None)
    if env is None:
        v = style(varname, fg='cyan', bold=True)
        echo(f"Environment variable {v} is not set.")
        secho("Aborting", fg='red', bold=True)
        return
    path = Path(env)
    assert path.is_dir()

    files = path.glob("**/*.xml")
    iterfiles(import_datafile, files)