# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
""" Main CLI entry point """

import logging
import sys
from contextlib import ExitStack
from pathlib import Path

import click
from packaging.version import Version
from rich import box, console, traceback
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

import imas
import imas.backends.imas_core.imas_interface
from imas import DBEntry, dd_zip
from imas.backends.imas_core.imas_interface import ll_interface
from imas.command.db_analysis import analyze_db, process_db_analysis
from imas.command.helpers import min_version_guard, setup_rich_log_handler
from imas.command.timer import Timer
from imas.exception import UnknownDDVersion

logger = logging.getLogger(__name__)


def _excepthook(type_, value, tb):
    logger.debug("Suppressed traceback:", exc_info=(type_, value, tb))
    # Only display the last traceback frame:
    if tb is not None:
        while tb.tb_next:
            tb = tb.tb_next
    rich_tb = traceback.Traceback.from_exception(type_, value, tb, extra_lines=0)
    console.Console(stderr=True).print(rich_tb)


@click.group("imas", invoke_without_command=True, no_args_is_help=True)
def cli():
    """imas-python command line interface.

    Please use one of the available commands listed below. You can get help for each
    command by executing:

        imas <command> --help
    """
    # Limit the traceback to 1 item: avoid scaring CLI users with long traceback prints
    # and let them focus on the actual error message
    sys.excepthook = _excepthook


cli.add_command(analyze_db)
cli.add_command(process_db_analysis)


@cli.command("version")
def print_version():
    """Print version information of imas-python."""
    cons = console.Console()
    grid = Table(
        title="imas-python version info", show_header=False, title_style="bold"
    )
    grid.box = box.HORIZONTALS
    if cons.size.width > 120:
        grid.width = 120
    grid.add_row("imas-python version:", imas.__version__)
    grid.add_section()
    grid.add_row("Default data dictionary version:", imas.IDSFactory().dd_version)
    dd_versions = ", ".join(imas.dd_zip.dd_xml_versions())
    grid.add_row("Available data dictionary versions:", dd_versions)
    grid.add_section()
    try:
        grid.add_row("Access Layer core version:", ll_interface.get_al_version())
    except Exception:
        grid.add_row("Access Layer core version:", "N/A")
    console.Console().print(grid)


@cli.command("print", no_args_is_help=True)
@click.argument("uri")
@click.argument("ids")
@click.argument("occurrence", default=0)
@click.option(
    "--all",
    "-a",
    "print_all",
    is_flag=True,
    help="Also show nodes with empty/default values",
)
def print_ids(uri, ids, occurrence, print_all):
    """Pretty print the contents of an IDS.

    \b
    uri         URI of the Data Entry (e.g. "imas:mdsplus?path=testdb").
    ids         Name of the IDS to print (e.g. "core_profiles").
    occurrence  Which occurrence to print (defaults to 0).
    """
    min_version_guard(Version("5.0"))
    setup_rich_log_handler(False)

    with DBEntry(uri, "r") as dbentry:
        ids_obj = dbentry.get(ids, occurrence, autoconvert=False)
        imas.util.print_tree(ids_obj, not print_all)


@cli.command("convert", no_args_is_help=True)
@click.argument("uri_in")
@click.argument("dd_version")
@click.argument("uri_out")
@click.option(
    "--ids",
    default="*",
    help="Specify which IDS to convert. \
If not provided, all IDSs in the data entry are converted.",
)
@click.option("--occurrence", default=-1, help="Specify which occurrence to convert.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress output.")
@click.option("--timeit", is_flag=True, help="Show timing information.")
@click.option(
    "--no-provenance",
    is_flag=True,
    help="Don't add provenance metadata to the converted IDS.",
)
def convert_ids(
    uri_in, dd_version, uri_out, ids, occurrence, quiet, timeit, no_provenance
):
    """Convert a Data Entry (or a single IDS) to the target DD version.

    Provide a different backend to URI_OUT than URI_IN to convert between backends.
    For example:

        imas convert imas:mdsplus?path=db-in 3.41.0 imas:hdf5?path=db-out

    \b
    uri_in      URI of the input Data Entry.
    dd_version  Data dictionary version to convert to. Can also be the path to an
                IDSDef.xml to convert to a custom/unreleased DD version.
    uri_out     URI of the output Data Entry.
    """
    min_version_guard(Version("5.1"))
    setup_rich_log_handler(quiet)

    # Check if we can load the requested version
    if dd_version in dd_zip.dd_xml_versions():
        version_params = dict(dd_version=dd_version)
    elif Path(dd_version).exists():
        version_params = dict(xml_path=dd_version)
    else:
        raise UnknownDDVersion(dd_version, dd_zip.dd_xml_versions())

    provenance_origin_uri = ""
    if not no_provenance:
        provenance_origin_uri = uri_in

    # Use an ExitStack to avoid three nested with-statements
    with ExitStack() as stack:
        entry_in = stack.enter_context(DBEntry(uri_in, "r"))
        entry_out = stack.enter_context(DBEntry(uri_out, "x", **version_params))

        # First build IDS/occurrence list so we can show a decent progress bar
        ids_list = [ids] if ids != "*" else entry_out.factory.ids_names()
        idss_with_occurrences = []
        for ids_name in ids_list:
            if occurrence == -1:
                idss_with_occurrences.extend(
                    (ids_name, occ) for occ in entry_in.list_all_occurrences(ids_name)
                )
            else:
                idss_with_occurrences.append((ids_name, occurrence))

        # Create progress bar and task
        columns = (
            TimeElapsedColumn(),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn("simpleDots", style="[white]"),
        )
        progress = stack.enter_context(Progress(*columns, disable=quiet))
        task = progress.add_task("Converting", total=len(idss_with_occurrences) * 3)
        # Create timer for timing get/convert/put
        timer = Timer("Operation", "IDS/occurrence")

        # Convert all IDSs
        for ids_name, occurrence in idss_with_occurrences:
            name = f"[bold green]{ids_name}[/][green]/{occurrence}[/]"

            progress.update(task, description=f"Reading {name}")
            with timer("Get", name):
                ids = entry_in.get(ids_name, occurrence, autoconvert=False)

            progress.update(task, description=f"Converting {name}", advance=1)
            # Explicitly convert instead of auto-converting during put. This is a bit
            # slower, but gives better diagnostics:
            if ids._dd_version == entry_out.dd_version:
                ids2 = ids
            else:
                with timer("Convert", name):
                    ids2 = imas.convert_ids(
                        ids,
                        None,
                        factory=entry_out.factory,
                        provenance_origin_uri=provenance_origin_uri,
                    )

            # Store in output entry:
            progress.update(task, description=f"Storing {name}", advance=1)
            with timer("Put", name):
                entry_out.put(ids2, occurrence)

            # Update progress bar
            progress.update(task, advance=1)

    # Display timing information
    if timeit:
        console.Console().print(timer.get_table("Time required per IDS"))


@cli.command("validate_nc", no_args_is_help=True)
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
def validate_nc(filename):
    """Validate if the provided netCDF file adheres to the IMAS conventions."""
    from imas.backends.netcdf.nc_validate import validate_netcdf_file

    try:
        validate_netcdf_file(filename)
    except Exception as exc:
        click.echo(f"File `{filename}` does not adhere to the IMAS conventions:")
        click.echo(exc)
        sys.exit(1)
    click.echo(f"File `{filename}` is a valid IMAS netCDF file.")


if __name__ == "__main__":
    cli()
