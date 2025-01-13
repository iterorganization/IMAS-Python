# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""
Helper module for providing a version-independent interface to the Access Layer.

This module tries to abstract away most API incompatibilities between the supported
Access Layer versions (for example the rename of _ual_lowlevel to _al_lowlevel).
"""
import inspect
import logging

from packaging.version import Version

logger = logging.getLogger(__name__)


# Import the Access Layer module
has_imas = True
try:
    # First try to import imas_core, which is available since AL 5.2
    from imas_core import _al_lowlevel as lowlevel
    from imas_core import imasdef

    # Enable throwing exceptions from the _al_lowlevel interface
    enable_exceptions = getattr(lowlevel, "imas_core_config_enable_exceptions", None)
    if enable_exceptions:
        enable_exceptions()

except ImportError as exc:
    imas = None
    has_imas = False
    imasdef = None
    lowlevel = None
    logger.critical(
        "Could not import 'al_core': %s. Some functionality is not available.",
        exc,
    )


class LLInterfaceError(RuntimeError):
    """Exception thrown when a method doesn't exist on the lowlevel interface."""


class LowlevelInterface:
    """Compatibility object.

    Provides a stable API for the rest of imas-python even when the
    `imas.lowlevel` interface changes.

    .. rubric:: Developer notes

    - When initializing the singleton object, we determine the AL version and redefine
      all methods that exist in the imported lowlevel module.
    - If the lowlevel introduces new methods, we need to:

      - Add a new method with the same name but prefix dropped (e.g. register_plugin
        for lowlevel.al_register_plugin)
      - The implementation of this method should provide a proper error message when
        the method is called and the underlying lowlevel doesn't provide the
        functionality. For instance ``raise self._minimal_version("5.0")``.

    - If the lowlevel drops methods, we need to update the implementation fo the method
      to provide a proper error message or a workaround.
    - Renamed methods (if this will ever happen) are perhaps best handled in the
      ``__init__`` by providing a mapping of new to old name, so far this was only
      relevant for the ``ual_`` to ``al_`` rename.
    """

    def __init__(self, lowlevel):
        self._lowlevel = lowlevel
        self._al_version = None
        self._al_version_str = ""
        public_methods = [attr for attr in dir(self) if not attr.startswith("_")]

        # AL not available
        if self._lowlevel is None:
            # Replace all our public methods by _imas_not_available
            for method in public_methods:
                setattr(self, method, self._imas_not_available)
            return

        # Lowlevel available, try to determine AL version
        if hasattr(lowlevel, "get_al_version"):
            # Introduced after 5.0.0
            self._al_version_str = self._lowlevel.get_al_version()
            self._al_version = Version(self._al_version_str)
        elif hasattr(lowlevel, "al_read_data"):
            # In AL 5.0.0, all `ual_` methods were renamed to `al_`
            self._al_version_str = "5.0.0"
            self._al_version = Version(self._al_version_str)
        else:
            # AL 4, don't try to determine in more detail
            self._al_version_str = "4.?.?"
            self._al_version = Version("4")
            public_methods.remove("close_pulse")

        if self._al_version < Version("5"):
            method_prefix = "ual_"
        else:
            method_prefix = "al_"
        # Overwrite all of our methods that are implemented in the lowlevel
        for method in public_methods:
            ll_method = getattr(lowlevel, method_prefix + method, None)
            if ll_method is not None:
                setattr(self, method, ll_method)

    def _imas_not_available(self, *args, **kwargs):
        raise RuntimeError(
            "This function requires an imas installation, which is not available."
        )

    def _minimal_version(self, minversion):
        return LLInterfaceError(
            f"This function requires at least Access Layer version {minversion}, "
            f"but the current version is {self._al_version_str}"
        )

    # AL 4 lowlevel API

    def begin_pulse_action(self, backendID, shot, run, user, tokamak, version):
        # Removed in AL5, compatibility handled in DBEntry
        raise LLInterfaceError(f"{__name__} is not implemented")

    def open_pulse(self, pulseCtx, mode, options):
        # Removed in AL5, compatibility handled in DBEntry
        raise LLInterfaceError(f"{__name__} is not implemented")

    def close_pulse(self, pulseCtx, mode):
        # options argument (mandatory in AL4) was removed in AL5
        # This method is overwritten in AL5, but for AL4 we need to do this:
        return lowlevel.ual_close_pulse(pulseCtx, mode, None)

    def begin_global_action(self, pulseCtx, dataobjectname, rwmode, datapath=""):
        # datapath was added in AL5 to support more efficient partial_get in the
        # UDA backend. TODO: figure out if this is useful for lazy loading.
        raise LLInterfaceError(f"{__name__} is not implemented")

    def begin_slice_action(self, pulseCtx, dataobjectname, rwmode, time, interpmode):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def end_action(self, ctx):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def write_data(self, ctx, pyFieldPath, pyTimebasePath, inputData):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def read_data(self, ctx, fieldPath, pyTimebasePath, ualDataType, dim):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def delete_data(self, ctx, path):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def begin_arraystruct_action(self, ctx, path, pyTimebase, size):
        raise LLInterfaceError(f"{__name__} is not implemented")

    def iterate_over_arraystruct(self, aosctx, step):
        raise LLInterfaceError(f"{__name__} is not implemented")

    # New methods added in AL 5.0

    def build_uri_from_legacy_parameters(
        self, backendID, pulse, run, user, tokamak, version, options
    ):
        raise self._minimal_version("5.0")

    def begin_dataentry_action(self, uri, mode):
        raise self._minimal_version("5.0")

    def register_plugin(self, name):
        raise self._minimal_version("5.0")

    def unregister_plugin(self, name):
        raise self._minimal_version("5.0")

    def bind_plugin(self, path, name):
        raise self._minimal_version("5.0")

    def unbind_plugin(self, path, name):
        raise self._minimal_version("5.0")

    def bind_readback_plugins(self, ctx):
        raise self._minimal_version("5.0")

    def unbind_readback_plugins(self, ctx):
        raise self._minimal_version("5.0")

    def write_plugins_metadata(self, ctx):
        raise self._minimal_version("5.0")

    def setvalue_parameter_plugin(self, parameter_name, inputData, pluginName):
        raise self._minimal_version("5.0")

    # New methods added in AL 5.1

    def get_occurrences(self, ctx, ids_name):
        raise self._minimal_version("5.1")

    def get_al_version(self):
        return self._al_version_str

    # New methods added in AL 5.4

    def begin_timerange_action(
        self, ctx, path, rwmode, tmin, tmax, dtime, interpolation_method
    ):
        raise self._minimal_version("5.4")


# Dummy documentation for interface:
for funcname in dir(LowlevelInterface):
    func = getattr(LowlevelInterface, funcname)
    if not funcname.startswith("_") and inspect.isfunction(func) and not func.__doc__:
        func.__doc__ = f"Wrapper function for AL lowlevel method ``{funcname}``"

ll_interface = LowlevelInterface(lowlevel)
"""imas-python <-> IMAS lowlevel interface"""
