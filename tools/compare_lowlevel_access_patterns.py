"""Compare the access patterns of the lowlevel AL API between imas-python and the HLI.
"""

from functools import wraps
from pathlib import Path
import sys
import traceback

import click

import imas
import imas
from imas.test.test_helpers import fill_with_random_data
from imas.ids_defs import IDS_TIME_MODE_HETEROGENEOUS


class ALWrapper:
    def __init__(self, al_module):
        self._al = al_module
        self._log = []

    def __getattr__(self, name):
        value = getattr(self._al, name)
        if callable(value):

            @wraps(value)
            def wrapper(*args, **kwargs):
                self._log.append((name, str(args), str(kwargs)))
                return value(*args, **kwargs)

            return wrapper
        return value


# Monkeypatch _al_lowlevel
wrapper = ALWrapper(sys.modules["imas._al_lowlevel"])
imas._al_lowlevel = wrapper
for item in sys.modules:
    if item.startswith("imas") and item.endswith("._al_lowlevel"):
        sys.modules[item] = wrapper
# And the imported locals in all imas modules
for item in sys.modules:
    if item.startswith("imas"):
        for alias in "_al_lowlevel", "ll":
            if hasattr(sys.modules[item], alias):
                setattr(sys.modules[item], alias, wrapper)


def compare_ids_put(imas_ids, hli_ids):
    imas._al_lowlevel._log.clear()
    # Start with hli IDS
    dbentry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "ITER", 1, 1, "test")
    dbentry.create()
    try:
        dbentry.put(hli_ids)
    except Exception as exc:
        print("Caught error while putting hli ids:", exc)
        traceback.print_exc()
    dbentry.close()
    hli_log = imas._al_lowlevel._log
    imas._al_lowlevel._log = []
    # And then the imas IDS
    dbentry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "ITER", 1, 1, "test")
    dbentry.create()
    try:
        dbentry.put(imas_ids)
    except Exception as exc:
        print("Caught error while putting imas ids:", exc)
        traceback.print_exc()
    dbentry.close()
    imas_log = imas._al_lowlevel._log
    imas._al_lowlevel._log = []
    hli_log_text = "\n".join("\t".join(item) for item in hli_log)
    imas_log_text = "\n".join("\t".join(item) for item in imas_log)
    Path("/tmp/hli.log").write_text(hli_log_text)
    Path("/tmp/imas.log").write_text(imas_log_text)
    print("Logs stored in /tmp/hli.log and /tmp/imas.log")


def compare_ids_get(imas_ids):
    # First put the ids
    idbentry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "ITER", 1, 1, "test")
    idbentry.create()
    idbentry.put(imas_ids)

    dbentry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "ITER", 1, 1, "test")
    dbentry.open()
    # Start with hli IDS
    imas._al_lowlevel._log.clear()
    dbentry.get(imas_ids.metadata.name)
    hli_log = imas._al_lowlevel._log
    imas._al_lowlevel._log = []
    # And then the imas IDS
    idbentry.get(imas_ids.metadata.name)
    imas_log = imas._al_lowlevel._log
    imas._al_lowlevel._log = []
    # Cleanup
    dbentry.close()
    idbentry.close()
    hli_log_text = "\n".join("\t".join(item) for item in hli_log)
    imas_log_text = "\n".join("\t".join(item) for item in imas_log)
    Path("/tmp/hli.log").write_text(hli_log_text)
    Path("/tmp/imas.log").write_text(imas_log_text)
    print("Logs stored in /tmp/hli.log and /tmp/imas.log")


@click.command()
@click.argument("ids_name")
@click.argument("method", type=click.Choice(["put", "get"]))
@click.option(
    "--heterogeneous",
    is_flag=True,
    help="Use heterogeneous time mode instead of homogeneous time.",
)
def main(ids_name, method, heterogeneous):
    """Compare lowlevel calls done by imas-python vs. the Python HLI

    This program fills the provided IDS with random data, then does I/O with it using
    both the Python HLI and the imas-python APIs. The resulting calls to the lowlevel Access
    Layer are logged to respectively /tmp/hli.log and /tmp/imas.log.

    You may use your favorite diff tool to compare the two files.

    \b
    IDS_NAME:   The name of the IDS to use for testing, for example "core_profiles".
    """
    imas_ids = imas.IDSFactory().new(ids_name)
    hli_ids = getattr(imas, ids_name)()

    fill_with_random_data(imas_ids)
    hli_ids.deserialize(imas_ids.serialize())

    if heterogeneous:
        # Change time mode
        time_mode = IDS_TIME_MODE_HETEROGENEOUS
        imas_ids.ids_properties.homogeneous_time = time_mode
        hli_ids.ids_properties.homogeneous_time = time_mode

    if method == "put":
        compare_ids_put(imas_ids, hli_ids)
    elif method == "get":
        compare_ids_get(imas_ids)


if __name__ == "__main__":
    main()
