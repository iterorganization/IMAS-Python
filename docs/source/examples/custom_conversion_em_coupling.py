"""IMAS-Python example for custom conversion logic.

This example script loads a Data Entry (in Data Dictionary 3.38.1) created by
DINA and converts the em_coupling IDS to DD 4.0.0.
"""

import imas
from imas.ids_defs import IDS_TIME_MODE_INDEPENDENT

input_uri = "imas:hdf5?path=/work/imas/shared/imasdb/ITER_SCENARIOS/3/105013/1"
# An error is reported when there's already data at the output_uri!
output_uri = "imas:hdf5?path=105013-1-converted"
target_dd_version = "4.0.0"


# Mapping of DD 3.38.1 em_coupling data to DD 4.0.0
# Map the name of the matrix in DD 3.38.1 to the identifier and coordinate URIs
COUPLING_MAPS = {
    "field_probes_active": dict(
        coupling_quantity=2,
        rows_uri="#magnetics/b_field_pol_probe",
        columns_uri="#pf_active/coil",
    ),
    "field_probes_grid": dict(
        coupling_quantity=2,
        rows_uri="#magnetics/b_field_pol_probe",
        columns_uri="#pf_plasma/element",
    ),
    "field_probes_passive": dict(
        coupling_quantity=2,
        rows_uri="#magnetics/b_field_pol_probe",
        columns_uri="#pf_passive/loop",
    ),
    "mutual_active_active": dict(
        coupling_quantity=1,
        rows_uri="#pf_active/coil",
        columns_uri="#pf_active/coil",
    ),
    "mutual_grid_active": dict(
        coupling_quantity=1,
        rows_uri="#pf_plasma/element",
        columns_uri="#pf_active/coil",
    ),
    "mutual_grid_grid": dict(
        coupling_quantity=1,
        rows_uri="#pf_plasma/element",
        columns_uri="#pf_plasma/element",
    ),
    "mutual_grid_passive": dict(
        coupling_quantity=1,
        rows_uri="#pf_plasma/element",
        columns_uri="#pf_passive/loop",
    ),
    "mutual_loops_active": dict(
        coupling_quantity=1,
        rows_uri="#magnetics/flux_loop",
        columns_uri="#pf_active/coil",
    ),
    "mutual_loops_passive": dict(
        coupling_quantity=1,
        rows_uri="#magnetics/flux_loop",
        columns_uri="#pf_passive/loop",
    ),
    "mutual_loops_grid": dict(
        coupling_quantity=1,
        rows_uri="#magnetics/flux_loop",
        columns_uri="#pf_plasma/element",
    ),
    "mutual_passive_active": dict(
        coupling_quantity=1,
        rows_uri="#pf_passive/loop",
        columns_uri="#pf_active/coil",
    ),
    "mutual_passive_passive": dict(
        coupling_quantity=1,
        rows_uri="#pf_passive/loop",
        columns_uri="#pf_passive/loop",
    ),
}


with (
    imas.DBEntry(input_uri, "r") as entry,
    imas.DBEntry(output_uri, "x", dd_version=target_dd_version) as out,
):
    print("Loaded IMAS Data Entry:", input_uri)

    print("This data entry contains the following IDSs:")
    filled_idss = []
    for idsname in entry.factory.ids_names():
        occurrences = entry.list_all_occurrences(idsname)
        if occurrences:
            filled_idss.append(idsname)
            print(f"- {idsname}, occurrences: {occurrences}")
    print("")

    # Load and convert all IDSs (except em_coupling) with imas.convert_ids()
    # N.B. we know that the input URI doesn't have multiple occurrences, so
    # we do not need to worry about them:
    for idsname in filled_idss:
        if idsname == "em_coupling":
            continue

        print(f"Loading IDS: {idsname}...")
        ids = entry.get(idsname, autoconvert=False)
        print(f"Converting IDS {idsname} to DD {target_dd_version}...")
        ids4 = imas.convert_ids(
            ids,
            target_dd_version,
            provenance_origin_uri=input_uri,
        )
        print(f"Storing IDS {idsname} to output data entry...")
        out.put(ids4)

    print("Conversion for em_coupling:")
    emc = entry.get("em_coupling", autoconvert=False)
    print("Using standard convert, this may log warnings about discarding data")
    emc4 = imas.convert_ids(
        emc,
        target_dd_version,
        provenance_origin_uri=input_uri,
    )

    print("Starting custom conversion of the coupling matrices")
    for matrix_name, mapping in COUPLING_MAPS.items():
        # Skip empty matrices
        if not emc[matrix_name].has_value:
            continue

        # Allocate a new coupling_matrix AoS element
        emc4.coupling_matrix.resize(len(emc4.coupling_matrix) + 1, keep=True)
        # And fill it

        emc4.coupling_matrix[-1].name = matrix_name
        # Assigning an integer to the identifier will automatically fill the
        # index/name/description. See documentation:
        # https://imas-python.readthedocs.io/en/latest/identifiers.html
        emc4.coupling_matrix[-1].quantity = mapping["coupling_quantity"]
        emc4.coupling_matrix[-1].rows_uri = [mapping["rows_uri"]]
        emc4.coupling_matrix[-1].columns_uri = [mapping["columns_uri"]]
        emc4.coupling_matrix[-1].data = emc[matrix_name].value
        # N.B. the original data has no error_upper/error_lower so we skip these
    # Store em_coupling IDS
    out.put(emc4)

    print("Generating pf_plasma IDS...")
    # N.B. This logic is specific to DINA
    # Create a new pf_plasma IDS and set basic properties
    pf_plasma = out.factory.pf_plasma()
    pf_plasma.ids_properties.homogeneous_time = IDS_TIME_MODE_INDEPENDENT
    pf_plasma.ids_properties.comment = "PF Plasma generated from equilibrium"

    equilibrium = entry.get("equilibrium", lazy=True, autoconvert=False)
    r = equilibrium.time_slice[0].profiles_2d[0].grid.dim1
    z = equilibrium.time_slice[0].profiles_2d[0].grid.dim2
    nr, nz = len(r), len(z)
    # Generate a pf_plasma element for each grid point:
    pf_plasma.element.resize(nr * nz)
    for ir, rval in enumerate(r):
        for iz, zval in enumerate(z):
            element = pf_plasma.element[ir * nr + iz]
            element.geometry.geometry_type = 2  # rectangle
            element.geometry.rectangle.r = rval
            element.geometry.rectangle.z = zval
    # Store pf_plasma IDS
    out.put(pf_plasma)

print("Conversion finished")
