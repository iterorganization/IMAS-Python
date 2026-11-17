from typing import Dict, List, Tuple, Union
import numpy as np
from . import IDSFactory
from .ids_convert import convert_ids
from .dd_zip import parse_dd_version
from .ids_toplevel import IDSToplevel
from .backends.netcdf.ids_tensorizer import IDSTensorizer

try:
    import awkward as ak
except ImportError:
    ak = None


def _recursively_put(location, value, ids):
    """
    Traverses the hierarchy of an `ids` object and deposits `value` at 
    `location`
    """
    # time_slice.profiles_1d.psi
    if "." in location:
        position, sub_location = location.split(".", 1)
        sub_ids = getattr(ids, position)
        if hasattr(sub_ids, "size"):
            N = len(value)
            if sub_ids.size == 0:
                sub_ids.resize(N)
            elif sub_ids.size != N:
                raise ValueError(
                    f"Inconsistent size across flat entries {location}, "
                    f"{N} (flat) vs. ids {sub_ids.size}!"
                )
            # Need to iterate over indices (e.g. equilibrium.time_slice[:].)
            for index in range(N):
                _recursively_put(sub_location, value[index], sub_ids[index])
        else:
            # Need to set an attribute
            # Now get the new substring, e.g. time_slice
            position, sub_location = location.split(".", 1)
            _recursively_put(sub_location, value, sub_ids)
    else:
        setattr(ids, location, value)
    return ids


def wrangle(flat: Dict, source_version: str) -> Dict[str, IDSToplevel]:
    """
    Takes a `flat` dictionary of awkward|numpy arrays represented in the 
    `source_version` and deposits each field in hierarchial IDS objects.
    Returns a dictionary of the populated IDS.

    Note: This does not perform any consistency checking to avoid performance
    impacts. A future `safe_wrangle` could wrap this function and perform a subsequent 
    consistency check. 
    """
    wrangled = {}
    factory = IDSFactory(source_version)
    for key in flat:
        ids, location = key.split(".", 1)
        if ids not in wrangled:
            wrangled[ids] = getattr(factory, ids)()
        wrangled[ids] = recursively_put(location, flat[key], wrangled[ids])
    return wrangled


def _split_location_across_ids(locations: List[str]) -> Dict[str, List[str]]:
    """
    Helper function that groups a list of imas_composer style `locations`
    into IDS-groups
    """
    ids_locations = {}
    for location in locations:
        ids, path = location.split(".", 1)
        if ids not in ids_locations:
            ids_locations[ids] = []
        ids_locations[ids].append(path.replace(".", "/"))
    return ids_locations


def unwrangle(
    locations: List[str],
    ids_dict: Dict[str, IDSToplevel],
    target_version: str | None = None,
) -> Tuple[Dict[str, Union[np.ndarray, object]], List[str]]:
    """
    Uses the IDSTensorizer to extract desired `locations` (imas_composer style) from a dictionary
    of ids_dict and stores them in a dictionary of flat dictionary.
    Automatically converts to `target_version` if specified.
    """
    flat = {}
    ids_locations = _split_location_across_ids(locations)
    failed_locations = []
    for key in ids_locations:
        ids = ids_dict[key]
        if target_version is not None and parse_dd_version(
            ids._dd_version
        ) != parse_dd_version(target_version):
            ids = convert_ids(ids, target_version)
        tensorizer = IDSTensorizer(ids, ids_locations[key])
        tensorizer.include_coordinate_paths()
        tensorizer.collect_filled_data()
        tensorizer.determine_data_shapes()
        # Add IDS conversion
        for ids_location in ids_locations[key]:
            location = key + "." + ids_location.replace("/", ".")
            try:
                values = tensorizer.awkward_tensorize(ids_location)
            except KeyError:
                failed_locations.append(location)
                continue
            if hasattr(values, "__getitem__"):
                # Not a scalar, e.g. homogenous_time
                try:
                    flat[location] = np.asarray(values)
                except ValueError:
                    if ak is not None:
                        flat[location] = ak.Array(values)
                    else:
                        raise ImportError(
                            "awkward-array is required to convert non-standard arrays. "
                            "Install it with: pip install imas-python[awkward]"
                        ) from None
            else:
                flat[location] = values
    return flat, failed_locations
