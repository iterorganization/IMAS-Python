import pytest
import numpy as np

try:
    import awkward as ak
except ImportError as exc:
    raise ImportError(
        "awkward-array is required" "Install it with: pip install imas-python[awkward]"
    ) from exc

from imas.wrangler import wrangle, unwrangle
from imas.ids_factory import IDSFactory
from imas.util import idsdiffgen


@pytest.fixture
def test_data():
    data = {"equilibrium": {}}
    data["equilibrium"]["N_time"] = 100
    data["equilibrium"]["N_radial"] = 100
    data["equilibrium"]["N_grid"] = 1
    data["equilibrium"]["time"] = np.linspace(0.0, 5.0, data["equilibrium"]["N_time"])
    data["equilibrium"]["psi_1d"] = np.linspace(
        0.0, 1.0, data["equilibrium"]["N_radial"]
    )
    data["equilibrium"]["r"] = np.linspace(1.0, 2.0, data["equilibrium"]["N_radial"])
    data["equilibrium"]["z"] = np.linspace(-1.0, 1.0, data["equilibrium"]["N_radial"])
    r_grid, z_grid = np.meshgrid(
        data["equilibrium"]["r"], data["equilibrium"]["z"], indexing="ij"
    )
    data["equilibrium"]["psi_2d"] = (r_grid - 1.5) ** 2 + z_grid**2

    data["thomson_scattering"] = {}
    data["thomson_scattering"]["N_ch"] = (20, 10)
    N = data["thomson_scattering"]["N_ch"][0] + data["thomson_scattering"]["N_ch"][1]
    data["thomson_scattering"]["identifier"] = np.asarray(
        "channel_" + np.asarray(np.linspace(1, N + 1, N, dtype=int), dtype="|U2"),
        dtype="|U10",
    )
    data["thomson_scattering"]["N_time"] = (100, 300)
    data["thomson_scattering"]["r"] = np.concatenate(
        [
            np.ones(data["thomson_scattering"]["N_ch"][0]) * 1.6,
            np.ones(data["thomson_scattering"]["N_ch"][1]) * 1.7,
        ]
    )
    data["thomson_scattering"]["z"] = np.concatenate(
        [
            np.linspace(-1.0, 1.0, data["thomson_scattering"]["N_ch"][0]),
            np.linspace(-1.0, 1.0, data["thomson_scattering"]["N_ch"][1]),
        ]
    )
    data["thomson_scattering"]["t_e"] = data["thomson_scattering"]["z"] ** 2 * 5.0e3
    data["thomson_scattering"]["n_e"] = data["thomson_scattering"]["z"] ** 2 * 5.0e19
    data["thomson_scattering"]["time"] = (
        np.linspace(0, 5.0, data["thomson_scattering"]["N_time"][0]),
        np.linspace(0, 5.0, data["thomson_scattering"]["N_time"][1]),
    )
    return data


@pytest.fixture
def flat(test_data):
    flat = {}
    # Equilibrium test data
    flat["equilibrium.time"] = test_data["equilibrium"]["time"]
    flat["equilibrium.time_slice.time"] = test_data["equilibrium"]["time"]
    flat["equilibrium.ids_properties.homogeneous_time"] = 1
    flat["equilibrium.time_slice.profiles_1d.psi"] = np.zeros(
        (test_data["equilibrium"]["N_time"], test_data["equilibrium"]["N_radial"])
    )
    flat["equilibrium.time_slice.profiles_1d.psi"][:] = test_data["equilibrium"][
        "psi_1d"
    ]
    flat["equilibrium.time_slice.profiles_2d.grid.dim1"] = np.zeros(
        (
            test_data["equilibrium"]["N_time"],
            test_data["equilibrium"]["N_grid"],
            test_data["equilibrium"]["N_radial"],
        )
    )
    flat["equilibrium.time_slice.profiles_2d.grid.dim1"][:] = test_data["equilibrium"][
        "r"
    ][None, :]
    flat["equilibrium.time_slice.profiles_2d.grid.dim2"] = np.zeros(
        (
            test_data["equilibrium"]["N_time"],
            test_data["equilibrium"]["N_grid"],
            test_data["equilibrium"]["N_radial"],
        )
    )
    flat["equilibrium.time_slice.profiles_2d.grid.dim2"][:] = test_data["equilibrium"][
        "z"
    ][None, :]
    flat["equilibrium.time_slice.profiles_2d.psi"] = np.zeros(
        (
            test_data["equilibrium"]["N_time"],
            test_data["equilibrium"]["N_grid"],
            test_data["equilibrium"]["N_radial"],
            test_data["equilibrium"]["N_radial"],
        )
    )
    flat["equilibrium.time_slice.profiles_2d.psi"][:] = test_data["equilibrium"][
        "psi_2d"
    ][None, ...]
    # Thomson scattering test data (ragged)
    flat["thomson_scattering.channel.identifier"] = test_data["thomson_scattering"][
        "identifier"
    ]
    flat["thomson_scattering.ids_properties.homogeneous_time"] = 0
    flat["thomson_scattering.channel.t_e.time"] = ak.concatenate(
        [
            np.tile(
                test_data["thomson_scattering"]["time"][0],
                (test_data["thomson_scattering"]["N_ch"][0], 1),
            ),
            np.tile(
                test_data["thomson_scattering"]["time"][1],
                (test_data["thomson_scattering"]["N_ch"][1], 1),
            ),
        ]
    )
    flat["thomson_scattering.channel.t_e.data"] = ak.concatenate(
        [
            np.repeat(
                test_data["thomson_scattering"]["t_e"][
                    : test_data["thomson_scattering"]["N_ch"][0], None
                ],
                test_data["thomson_scattering"]["N_time"][0],
                axis=1,
            ),
            np.repeat(
                test_data["thomson_scattering"]["t_e"][
                    test_data["thomson_scattering"]["N_ch"][0] :, None
                ],
                test_data["thomson_scattering"]["N_time"][1],
                axis=1,
            ),
        ]
    )
    flat["thomson_scattering.channel.n_e.time"] = ak.concatenate(
        [
            np.tile(
                test_data["thomson_scattering"]["time"][0],
                (test_data["thomson_scattering"]["N_ch"][0], 1),
            ),
            np.tile(
                test_data["thomson_scattering"]["time"][1],
                (test_data["thomson_scattering"]["N_ch"][1], 1),
            ),
        ]
    )
    flat["thomson_scattering.channel.n_e.data"] = ak.concatenate(
        [
            np.repeat(
                test_data["thomson_scattering"]["n_e"][
                    : test_data["thomson_scattering"]["N_ch"][0], None
                ],
                test_data["thomson_scattering"]["N_time"][0],
                axis=1,
            ),
            np.repeat(
                test_data["thomson_scattering"]["n_e"][
                    test_data["thomson_scattering"]["N_ch"][0] :, None
                ],
                test_data["thomson_scattering"]["N_time"][1],
                axis=1,
            ),
        ]
    )
    flat["thomson_scattering.channel.position.r"] = test_data["thomson_scattering"]["r"]
    flat["thomson_scattering.channel.position.z"] = test_data["thomson_scattering"]["z"]
    return flat


@pytest.fixture
def test_ids_dict(test_data):
    factory = IDSFactory("3.41.0")
    equilibrium = factory.equilibrium()
    equilibrium.time = test_data["equilibrium"]["time"]
    equilibrium.time_slice.resize(test_data["equilibrium"]["N_time"])
    equilibrium.ids_properties.homogeneous_time = 1
    for i in range(test_data["equilibrium"]["N_time"]):
        equilibrium.time_slice[i].time = test_data["equilibrium"]["time"][i]
        equilibrium.time_slice[i].profiles_1d.psi = test_data["equilibrium"]["psi_1d"]
        equilibrium.time_slice[i].profiles_2d.resize(1)
        equilibrium.time_slice[i].profiles_2d[0].grid.dim1 = test_data["equilibrium"][
            "r"
        ]
        equilibrium.time_slice[i].profiles_2d[0].grid.dim2 = test_data["equilibrium"][
            "z"
        ]
        equilibrium.time_slice[i].profiles_2d[0].psi = test_data["equilibrium"][
            "psi_2d"
        ]

    thomson_scattering = factory.thomson_scattering()
    thomson_scattering.ids_properties.homogeneous_time = 0
    N = (
        test_data["thomson_scattering"]["N_ch"][0]
        + test_data["thomson_scattering"]["N_ch"][1]
    )
    thomson_scattering.channel.resize(N)
    index = 0
    for i in range(N):
        if i == test_data["thomson_scattering"]["N_ch"][0]:
            index = 1
        thomson_scattering.channel[i].identifier = test_data["thomson_scattering"][
            "identifier"
        ][i]
        thomson_scattering.channel[i].t_e.time = test_data["thomson_scattering"][
            "time"
        ][index]
        thomson_scattering.channel[i].t_e.data = np.tile(
            test_data["thomson_scattering"]["t_e"][i],
            test_data["thomson_scattering"]["N_time"][index],
        )
        thomson_scattering.channel[i].n_e.time = test_data["thomson_scattering"][
            "time"
        ][index]
        thomson_scattering.channel[i].n_e.data = np.tile(
            test_data["thomson_scattering"]["n_e"][i],
            test_data["thomson_scattering"]["N_time"][index],
        )
        thomson_scattering.channel[i].position.r = test_data["thomson_scattering"]["r"][
            i
        ]
        thomson_scattering.channel[i].position.z = test_data["thomson_scattering"]["z"][
            i
        ]

    return {"equilibrium": equilibrium, "thomson_scattering": thomson_scattering}


def test_wrangle(test_ids_dict, flat):
    wrangled = wrangle(flat, source_version='3.41.0')
    for key in test_ids_dict:
        diff = idsdiffgen(wrangled[key], test_ids_dict[key])
        assert len(list(diff)) == 0, diff


def get_dtype(arr):
    """Get dtype from either numpy or awkward array."""
    if isinstance(arr, ak.Array):
        # Easiest way to extract the numpy dtype from an awkward array
        return eval("np." + arr.typestr.split("*")[-1])
    if hasattr(arr, "dtype"):
        return arr.dtype
    else:
        return type(arr)


def test_unwrangle(test_ids_dict, flat):
    result, failed = unwrangle(list(flat.keys()), test_ids_dict)
    assert len(failed) == 0, f"The following fields failed to load {failed}"
    for key in flat.keys():
        if np.issubdtype(get_dtype(result[key]), np.floating):
            assert ak.almost_equal(result[key], flat[key])
        else:
            assert ak.array_equal(result[key], flat[key])
