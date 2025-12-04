"""IMAS-Python-based command line tool for analysing fields in a database."""

import gzip
import json
import logging
import platform
import re
import readline
import sys
from csv import writer as csvwriter
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import click
import rich
import rich.panel
import rich.progress
import rich.table
import rich.text
import rich.tree

import imas
from imas.command.helpers import setup_rich_log_handler
from imas.ids_metadata import IDSMetadata

directory_path = click.Path(exists=True, file_okay=False, path_type=Path)
outfile_path = click.Path(dir_okay=False, writable=True, path_type=Path)
infile_path = click.Path(exists=True, dir_okay=False, readable=True, path_type=Path)

logger = logging.getLogger(__name__)


@click.command("analyze-db")
@click.argument("dbentry", nargs=-1, type=directory_path)
@click.option(
    "--output",
    "-o",
    type=outfile_path,
    default="imas-db-analysis.json.gz",
    help="Output file",
)
def analyze_db(dbentry: Iterable[Path], output: Path) -> None:
    """Analyze one or more Data Entries stored in the HDF5 backend format.

    This analysis will collect the following data:

    \b
    - The (host)name of the machine
    - The path to the Data Entry
    - Which IDSs are stored in the Data Entry
    - Which fields in the IDSs are filled

    \b
    Arguments:
    DBENTRY     Folder(s) containing IMAS data stored in the HDF5 backend format.

    \b
    Notes:
    1. This tool does not accept IMAS URIs, only folder names. To avoid loading all
       data, the IDSs are inspected by looking at the HDF5 files directly.
    2. This tool uses the optional `h5py` dependency. An error is raised when this
       package is not available.
    3. If your data is stored in another format than HDF5, you may use `imas convert`
       to convert the data into the HDF5 backend format first.
    """
    # Test if h5py is available
    try:
        import h5py  # noqa
    except ModuleNotFoundError:
        rich.print(
            "[red]Module [bold]h5py[/bold] is not available.[/]\n"
            "Please load the [bold]h5py[/] HPC module, or install "
            "[bold]h5py[/] with `[bold]pip install h5py[/bold]`.",
            file=sys.stderr,
        )
        sys.exit(1)
    setup_rich_log_handler(False)

    # Load existing data?
    if output.exists():
        logger.info("Existing data found. New data will be appended to it.")
        try:
            with gzip.open(output, "rt", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            logger.error("Could not read data from '%s'.", output, exc_info=True)
            logger.error("Please remove the file '%s' and try again.", output)
            sys.exit(1)
    else:
        data = []

    # Analyze provided paths
    for entry in rich.progress.track(dbentry, transient=True):
        # Check if a master.h5 is present
        if not (entry / "master.h5").exists:
            logger.error("Could not find '%s/master.h5', skipping this folder.", entry)
            continue
        result = analyze_folder(entry)
        data.append(result)

    if data:
        with gzip.open(output, "wt", encoding="utf-8") as file:
            json.dump(data, file)
        logger.info(f"Output data is stored in {output}")


def analyze_folder(entry: Path):
    """Analyze a folder with HDF5 files, returning a structure containing IDS usage."""
    return {
        "machine_name": platform.node(),
        "dbentry_path": str(entry),
        "ids_info": [
            ids_info(idsfile)
            for idsfile in entry.glob("*.h5")
            if idsfile.stem != "master"
        ],
    }


def ids_info(idsfile: Path):
    """Open HDF5 ids file and return structure containing the filled data paths."""
    import h5py

    name_and_occurrence = idsfile.stem
    name, occurrence = re.split("_(?=[0-9]+)|$", name_and_occurrence, 1)
    filled_data = []
    with h5py.File(idsfile, "r") as f:
        group = f[name_and_occurrence]
        for dataset in group.keys():
            if dataset.endswith("SHAPE"):
                continue
            path = dataset.replace("[", "").replace("]", "").replace("&", "/")
            filled_data.append(path)

    return {
        "name": name,
        "occurrence": occurrence,
        "filled_data": filled_data,
    }


@dataclass
class _PathUsage:
    num_occurrences: int = 0
    path_counter: Counter = field(default_factory=Counter)


def _write_usage_stats_to_csv(
    writer, usage_per_entry, usage_per_occurrence, num_entries
):
    """Write usage statistics to csv file.

    Args:
        writer: an instance of csv.writer
        usage_per_entry: path usage statistics per data entry
        usage_per_occurrence: path usage statistics per occurrence
        num_entries: number of data entries
    """
    # Write header
    writer.writerow(
        [
            "IDS",
            "Path in IDS",
            "Uses errorbar",
            "Frequency (without occurrences)",
            "Frequency (with occurences)",
        ]
    )

    for ids_name in sorted(usage_per_entry):
        entry_usage = usage_per_entry[ids_name]
        occurrence_usage = usage_per_occurrence[ids_name]

        # Usage statistics of the IDS (# entries with this IDS / # entries)
        freq = entry_usage.num_occurrences / num_entries
        writer.writerow([ids_name, "", "", freq, ""])

        for path, entry_count in sorted(entry_usage.path_counter.items()):
            if "_error_" in path:
                continue  # Skip error nodes
            occurrence_count = occurrence_usage.path_counter[path]

            uses_error = f"{path}_error_upper" in entry_usage.path_counter
            # Frequency without occurrences, see GH#84 for details
            freq1 = entry_count / entry_usage.num_occurrences
            # Frequency with occurences
            freq2 = occurrence_count / occurrence_usage.num_occurrences

            # Write data row
            writer.writerow([ids_name, path, "X" if uses_error else "", freq1, freq2])


_csv_help_text = (
    "Write analysis output to the provided CSV file. For details, "
    "see https://github.com/iterorganization/IMAS-Python/issues/84."
)


@click.command("process-db-analysis")
@click.argument(
    "infiles", metavar="INPUT_FILES...", nargs=-1, type=infile_path, required=True
)
@click.option("--show-empty-ids", is_flag=True, help="Show empty IDSs in the overview.")
@click.option("--csv", type=outfile_path, help=_csv_help_text)
def process_db_analysis(infiles, show_empty_ids, csv):
    """Process supplied Data Entry analyses, and display statistics.

    \b
    Arguments:
    INPUT_FILES     File(s) produced by `imas analyze-db` to process.
    """
    setup_rich_log_handler(False)

    usage_per_entry = defaultdict(_PathUsage)
    usage_per_occurrence = defaultdict(_PathUsage)
    num_entries = 0

    logger.info("Reading %d input files...", len(infiles))

    # Read input data and collate usage info per IDS
    for fname in infiles:
        with gzip.open(fname, "rt", encoding="utf-8") as file:
            data = json.load(file)

        for entry in data:
            usage_for_this_entry = defaultdict(_PathUsage)
            for ids_info in entry["ids_info"]:
                ids_name = ids_info["name"]
                filled_paths = ids_info["filled_data"]
                # Update counters for this entry
                usage_for_this_entry[ids_name].path_counter.update(filled_paths)
                # Update counters for all occurrecnes
                usage_per_occurrence[ids_name].num_occurrences += 1
                usage_per_occurrence[ids_name].path_counter.update(filled_paths)
            # Update data entry usage
            for ids_name, usage in usage_for_this_entry.items():
                usage_per_entry[ids_name].num_occurrences += 1
                usage_per_entry[ids_name].path_counter.update(usage.path_counter.keys())
            num_entries += 1

    logger.info("Done reading input files.")

    if csv is not None:
        # Output to CSV file
        logger.info("Writing output to CSV file: %s", csv)
        with open(csv, "w") as csvfile:
            writer = csvwriter(csvfile)
            _write_usage_stats_to_csv(
                writer, usage_per_entry, usage_per_occurrence, num_entries
            )
        logger.info("Done.")
        return

    logger.info("Analyzing filled data...")
    factory = imas.IDSFactory()
    logger.info("Using Data Dictionary version %s.", factory.dd_version)

    # Construct AnalysisNodes per IDS
    analysis_nodes: Dict[str, _AnalysisNode] = {}
    for ids_name, usage in usage_per_occurrence.items():
        if ids_name not in factory.ids_names():
            logger.warning(
                "Founds IDS %s in data files, but this IDS is not available "
                "in DD version %s. Statistics will not be tracked.",
                ids_name,
                factory.dd_version,
            )
            continue
        metadata = factory.new(ids_name).metadata
        filled = set(usage.path_counter.keys())
        ids_analysis_node = _AnalysisNode("")

        def walk_metadata_tree(metadata: IDSMetadata, node: _AnalysisNode):
            """Recursively walk the IDSMetadata tree to check which nodes are filled."""
            for meta_child in metadata._children.values():
                path = meta_child.path_string
                childnode = _AnalysisNode(path, path in filled)
                node.children.append(childnode)

                if meta_child._children:  # Childnode is a structure/AoS itself
                    # Recurse
                    walk_metadata_tree(meta_child, childnode)
                    # Update node statistics
                    node.num_desc_nodes += childnode.num_desc_nodes
                    node.num_desc_nodes_filled += childnode.num_desc_nodes_filled
                else:  # Childnode is a data node
                    # Update node statistics
                    node.num_desc_nodes += 1
                    if childnode.used:
                        node.num_desc_nodes_filled += 1
            node.used = node.num_desc_nodes_filled > 0

        walk_metadata_tree(metadata, ids_analysis_node)
        analysis_nodes[ids_name] = ids_analysis_node

    # Display summary results per IDS
    logger.info("Analysis done. Printing results:")
    sorted_ids_names = sorted(
        analysis_nodes,
        key=lambda ids_name: -analysis_nodes[ids_name].fill_fraction,
    )
    table = rich.table.Table("IDS", "Filled nodes", caption="Usage summary")
    for ids_name in sorted_ids_names:
        node = analysis_nodes[ids_name]
        if node.num_desc_nodes_filled == 0 and not show_empty_ids:
            continue  # hide IDSs without data
        dim = "" if node.num_desc_nodes_filled > 0 else "[dim]"
        table.add_row(
            f"{dim}[bold]{ids_name}",
            f"{dim}{node.num_desc_nodes_filled: >4} / {node.num_desc_nodes: >4} "
            f"({node.fill_fraction: >6.2%})",
        )
    rich.print(table)

    # Use readline for autocompleting IDS names when pressing <tab>
    def rlcompleter(text, state) -> Optional[str]:
        matching_idss = [name for name in sorted_ids_names if name.startswith(text)]
        if state < len(matching_idss):
            return matching_idss[state]
        return None

    readline.set_completer(rlcompleter)
    readline.parse_and_bind("tab: complete")

    # Display input prompt for detailed results per IDS
    while True:
        # click.prompt doesn't work nicely with readline, so use builtin input():
        ids_name = input("Enter IDS name to show detailed usage [exit]: ").strip()

        if ids_name == "exit" or not ids_name:
            break
        elif ids_name not in analysis_nodes:
            rich.print(f"[red]Unknown IDS name: [bold]{ids_name}")
            continue

        node = analysis_nodes[ids_name]
        tree = rich.tree.Tree(
            f"[bold red]{ids_name}[/]: [bold cyan]{node.num_desc_nodes_filled}[/]/"
            f"[bold cyan]{node.num_desc_nodes}[/] data nodes filled"
        )
        for childnode in node.children:
            childnode.fill_tree(tree)
        rich.print(rich.panel.Panel(tree, expand=False))


@dataclass
class _AnalysisNode:
    """Data class to store analysis results for a node in an IDS."""

    path: str
    """Path of this node, e.g. "ids_properties/comment"."""
    used: bool = False
    """True when any analysed Data Entry had this node populated."""
    children: List["_AnalysisNode"] = field(repr=False, default_factory=list)
    """List of child nodes (when this is a structure or AoS node)."""
    num_desc_nodes = 0
    """Total descendent data (i.e. no structure/AoS) nodes."""
    num_desc_nodes_filled = 0
    """Total number of descendent data nodes that are used."""

    @property
    def fill_fraction(self):
        """The fill fraction of all descendent nodes."""
        return self.num_desc_nodes_filled / self.num_desc_nodes

    def fill_tree(self, tree: rich.tree.Tree):
        """Fill provided rich.tree.Tree with analysis data."""
        if not self.children:  # leaf node
            if not self.used:
                return  # skip empty leaf nodes
            label = f"[green]{self.path}[/] is used"
        else:
            label = (
                f"[blue]{self.path}[/]: [bold cyan]{self.num_desc_nodes_filled}[/]/"
                f"[bold cyan]{self.num_desc_nodes}[/] descendent nodes filled"
            )
            if self.num_desc_nodes_filled == 0:
                label = rich.text.Text.from_markup(label, style="dim")

        subtree = tree.add(label)
        if self.used:
            for child in self.children:
                child.fill_tree(subtree)
