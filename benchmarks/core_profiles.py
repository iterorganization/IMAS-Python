import datetime
import os

import numpy as np

import imas

from .utils import (
    available_backends,
    available_serializers,
    available_slicing_backends,
    create_dbentry,
)

N_SLICES = 32
TIME = np.linspace(0, 1000, N_SLICES)


def fill_slices(core_profiles, times):
    """Fill a time slice of a core_profiles IDS with generated data.

    Args:
        core_profiles: core_profiles IDS (either from IMAS-Python or AL Python)
        times: time values to fill a slice for
    """
    core_profiles.ids_properties.homogeneous_time = 1  # HOMOGENEOUS
    core_profiles.ids_properties.comment = (
        "Generated for the IMAS-Python benchmark suite"
    )
    core_profiles.ids_properties.creation_date = datetime.date.today().isoformat()
    core_profiles.code.name = "IMAS-Python ASV benchmark"
    core_profiles.code.version = imas.__version__
    core_profiles.code.repository = "https://github.com/iterorganization/IMAS-Python"

    core_profiles.time = np.array(times)
    core_profiles.profiles_1d.resize(len(times))
    for i, t in enumerate(times):
        profiles_1d = core_profiles.profiles_1d[i]
        # Fill in grid coordinate
        N_GRID = 1024
        profiles_1d.grid.rho_tor_norm = np.linspace(0, 1, N_GRID)
        gauss = np.exp(5 * profiles_1d.grid.rho_tor_norm**2)
        # Create some profiles
        noise = 0.8 + 0.4 * np.random.random_sample(N_GRID)
        profiles_1d.electrons.temperature = t * gauss * noise
        profiles_1d.electrons.density = t + gauss * noise
        ions = ["H", "D", "T"]
        profiles_1d.ion.resize(len(ions))
        profiles_1d.neutral.resize(len(ions))
        for i, ion in enumerate(ions):
            if hasattr(profiles_1d.ion[i], "label"):
                profiles_1d.ion[i].label = ion
                profiles_1d.neutral[i].label = ion
            if hasattr(profiles_1d.ion[i], "name"):
                profiles_1d.ion[i].name = ion
                profiles_1d.neutral[i].name = ion

            # profiles_1d.ion[i].label = profiles_1d.neutral[i].label = ion
            profiles_1d.ion[i].z_ion = 1.0
            profiles_1d.ion[i].neutral_index = profiles_1d.neutral[i].ion_index = i + 1

            noise = 0.8 + 0.4 * np.random.random_sample(N_GRID)
            profiles_1d.ion[i].temperature = t * gauss * noise + i
            profiles_1d.ion[i].density = t + gauss * noise + i

            profiles_1d.neutral[i].temperature = np.zeros(N_GRID)
            profiles_1d.neutral[i].density = np.zeros(N_GRID)


class GetSlice:
    params = [available_slicing_backends]
    param_names = ["backend"]

    def setup(self, backend):
        self.dbentry = create_dbentry(backend)
        core_profiles = imas.IDSFactory().core_profiles()
        fill_slices(core_profiles, TIME)
        self.dbentry.put(core_profiles)

    def time_get_slice(self, backend):
        for t in TIME:
            self.dbentry.get_slice("core_profiles", t, imas.ids_defs.CLOSEST_INTERP)

    def teardown(self, backend):
        if hasattr(self, "dbentry"):  # imas + netCDF has no dbentry
            self.dbentry.close()


class Get:
    params = [available_backends]
    param_names = ["backend"]
    setup = GetSlice.setup
    teardown = GetSlice.teardown

    def time_get(self, backend):
        self.dbentry.get("core_profiles")


class LazyGet:
    params = [[True, False], available_slicing_backends]
    param_names = ["lazy", "backend"]

    def setup(self, lazy, backend):
        self.dbentry = create_dbentry(backend)
        core_profiles = imas.IDSFactory().core_profiles()
        fill_slices(core_profiles, TIME)
        self.dbentry.put(core_profiles)

    def time_lazy_get(self, lazy, backend):
        cp = self.dbentry.get("core_profiles", lazy=lazy)
        np.array([prof_1d.electrons.temperature for prof_1d in cp.profiles_1d])

    def teardown(self, lazy, backend):
        if hasattr(self, "dbentry"):  # imas + netCDF has no dbentry
            self.dbentry.close()


class Generate:
    def setup(self):
        self.core_profiles = imas.IDSFactory().core_profiles()

    def time_generate(self):
        fill_slices(self.core_profiles, TIME)

    def time_generate_slices(self):
        for t in TIME:
            fill_slices(self.core_profiles, [t])

    def time_create_core_profiles(self):
        imas.IDSFactory().core_profiles()


class Put:
    params = [["0", "1"], available_backends]
    param_names = ["disable_validate", "hli", "backend"]

    def setup(self, disable_validate, backend):
        create_dbentry(backend).close()  # catch unsupported combinations
        self.core_profiles = imas.IDSFactory().core_profiles()
        fill_slices(self.core_profiles, TIME)
        os.environ["IMAS_AL_DISABLE_VALIDATE"] = disable_validate

    def time_put(self, disable_validate, backend):
        with create_dbentry(backend) as dbentry:
            dbentry.put(self.core_profiles)


class PutSlice:
    params = [["0", "1"], available_slicing_backends]
    param_names = ["disable_validate", "backend"]

    def setup(self, disable_validate, backend):
        create_dbentry(backend).close()  # catch unsupported combinations
        self.core_profiles = imas.IDSFactory().core_profiles()
        os.environ["IMAS_AL_DISABLE_VALIDATE"] = disable_validate

    def time_put_slice(self, disable_validate, backend):
        with create_dbentry(backend) as dbentry:
            for t in TIME:
                fill_slices(self.core_profiles, [t])
                dbentry.put_slice(self.core_profiles)


class Serialize:
    params = [available_serializers]
    param_names = ["serializer"]

    def setup(self, serializer):
        self.core_profiles = imas.IDSFactory().core_profiles()
        fill_slices(self.core_profiles, TIME)

    def time_serialize(self, serializer):
        self.core_profiles.serialize(serializer)


class Deserialize:
    params = [available_serializers]
    param_names = ["serializer"]

    def setup(self, serializer):
        self.core_profiles = imas.IDSFactory().core_profiles()
        fill_slices(self.core_profiles, TIME)
        self.data = self.core_profiles.serialize(serializer)
        self.core_profiles = imas.IDSFactory().core_profiles()

    def time_deserialize(self, serializer):
        self.core_profiles.deserialize(self.data)
