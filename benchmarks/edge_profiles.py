import datetime
import os

import numpy as np

import imas

from .utils import available_backends, create_dbentry, factory, hlis

N_POINTS = 600  # number of random R,Z points
N_LINES = 1200  # number of random lines in R,Z plane
N_SURFACES = 600  # number of random surfaces in R,Z plane
TIME = np.linspace(0, 1, 20)


def fill_ggd(edge_profiles, times):
    """Fill nested arrays of structures in grids_ggd and ggd substructures.

    Args:
        edge_profiles: edge_profiles IDS object (either from imas-python or AL HLI)
        times: time values to fill
    """
    edge_profiles.ids_properties.homogeneous_time = (
        imas.ids_defs.IDS_TIME_MODE_HETEROGENEOUS
    )
    edge_profiles.ids_properties.comment = "Generated for imas-python benchmark suite"
    edge_profiles.ids_properties.creation_date = datetime.date.today().isoformat()
    edge_profiles.code.name = "imas-python ASV benchmark"
    edge_profiles.code.version = imas.__version__
    edge_profiles.code.repository = (
        "https://github.com/iterorganization/imas-python"
    )

    # This GGD grid is not a valid description, but it's a good stress test for the
    # typical access patterns that exist in GGD grids
    edge_profiles.grid_ggd.resize(1)
    grid = edge_profiles.grid_ggd[0]
    grid.time = times[0]
    grid.identifier.name = "SN"
    grid.identifier.index = 4
    grid.identifier.description = "Single null"

    grid.space.resize(2)
    for i in range(2):
        grid.space[i].identifier.name = "Standard grid"
        grid.space[i].identifier.index = 1
        grid.space[i].identifier.description = "Description...."
        grid.space[i].geometry_type.index = 0
    grid.space[0].coordinates_type = np.array([4, 5], dtype=np.int32)
    grid.space[0].objects_per_dimension.resize(3)  # points, lines, surfaces
    points = grid.space[0].objects_per_dimension[0].object
    points.resize(N_POINTS)
    for i in range(N_POINTS):
        points[i].geometry = np.random.random_sample(2)
    lines = grid.space[0].objects_per_dimension[1].object
    lines.resize(N_LINES)
    for i in range(N_LINES):
        lines[i].nodes = np.random.randint(1, N_POINTS + 1, 2, dtype=np.int32)
    surfaces = grid.space[0].objects_per_dimension[2].object
    surfaces.resize(N_SURFACES)
    for i in range(N_SURFACES):
        surfaces[i].nodes = np.random.randint(1, N_LINES + 1, 4, dtype=np.int32)

    grid.space[1].coordinates_type = np.array([6], dtype=np.int32)
    grid.space[1].objects_per_dimension.resize(2)
    obp = grid.space[1].objects_per_dimension[0]
    obp.object.resize(2)
    obp.object[0].geometry = np.array([0.0])
    obp.object[0].nodes = np.array([1], dtype=np.int32)
    obp.object[1].geometry = np.array([2 * np.pi])
    obp.object[1].nodes = np.array([2], dtype=np.int32)
    obp = grid.space[1].objects_per_dimension[1]
    obp.object.resize(1)
    obp.object[0].boundary.resize(2)
    obp.object[0].boundary[0].index = 1
    obp.object[0].boundary[0].neighbours = np.array([0], dtype=np.int32)
    obp.object[0].boundary[0].index = 2
    obp.object[0].boundary[0].neighbours = np.array([0], dtype=np.int32)
    obp.object[0].nodes = np.array([1, 2], dtype=np.int32)
    obp.object[0].measure = 2 * np.pi

    grid.grid_subset.resize(3)
    for i in range(3):
        subset = grid.grid_subset[i]
        subset.identifier.name = ["nodes", "edges", "cells"][i]
        subset.identifier.index = [1, 2, 5][i]
        subset.dimension = [1, 2, 3][i]

    # Time for filling random data
    edge_profiles.ggd.resize(len(times))
    for i, t in enumerate(times):
        ggd = edge_profiles.ggd[i]
        ggd.time = t

        ggd.ion.resize(1)
        for i, quantity in enumerate(
            [
                ggd.electrons.temperature,
                ggd.electrons.density,
                ggd.electrons.pressure,
                ggd.ion[0].temperature,
                ggd.ion[0].density,
                ggd.ion[0].pressure,
            ]
        ):
            quantity.resize(1)
            quantity[0].grid_index = 1
            subset = i % 3
            quantity[0].grid_subset_index = subset + 1
            size = [N_POINTS, N_LINES, N_SURFACES][subset]
            quantity[0].values = np.random.random_sample(size)


class Get:
    params = [hlis, available_backends]
    param_names = ["hli", "backend"]

    def setup(self, hli, backend):
        self.dbentry = create_dbentry(hli, backend)
        edge_profiles = factory[hli].edge_profiles()
        fill_ggd(edge_profiles, TIME)
        self.dbentry.put(edge_profiles)

    def time_get(self, hli, backend):
        self.dbentry.get("edge_profiles")

    def teardown(self, hli, backend):
        if hasattr(self, "dbentry"):  # imas + netCDF has no dbentry
            self.dbentry.close()


class Generate:
    params = [hlis]
    param_names = ["hli"]

    def time_generate(self, hli):
        edge_profiles = factory[hli].edge_profiles()
        fill_ggd(edge_profiles, TIME)

    def time_create_edge_profiles(self, hli):
        factory[hli].edge_profiles()


class Put:
    params = [["0", "1"], hlis, available_backends]
    param_names = ["disable_validate", "hli", "backend"]

    def setup(self, disable_validate, hli, backend):
        create_dbentry(hli, backend).close()  # catch unsupported combinations
        self.edge_profiles = factory[hli].edge_profiles()
        fill_ggd(self.edge_profiles, TIME)
        os.environ["IMAS_AL_DISABLE_VALIDATE"] = disable_validate

    def time_put(self, disable_validate, hli, backend):
        with create_dbentry(hli, backend) as dbentry:
            dbentry.put(self.edge_profiles)
