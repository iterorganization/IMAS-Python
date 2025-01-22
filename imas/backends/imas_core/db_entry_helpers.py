# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Helper methods for loading data from and storing data to Data Entries.
"""

from typing import Optional

import numpy as np

from imas.ids_base import IDSBase
from imas.ids_convert import NBCPathMap
from imas.ids_data_type import IDSDataType
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS, IDS_TIME_MODE_INDEPENDENT
from imas.ids_metadata import IDSMetadata
from imas.ids_struct_array import IDSStructArray
from imas.ids_structure import IDSStructure

from .al_context import ALContext, LazyALContext


def get_children(
    structure: IDSStructure,
    ctx: ALContext,
    time_mode: int,
    nbc_map: Optional[NBCPathMap],
) -> None:
    """Recursively get all children of an IDSStructure."""
    # NOTE: changes in this method must be propagated to _get_child and vice versa
    #   Performance: this method is specialized for the non-lazy get

    for name, child_meta in structure._children.items():
        if time_mode == IDS_TIME_MODE_INDEPENDENT and child_meta.type.is_dynamic:
            continue  # skip dynamic (time-dependent) nodes

        path = child_meta.path_string
        data_type = child_meta.data_type

        if nbc_map and path in nbc_map:
            if nbc_map.path[path] is None:
                continue  # element does not exist in the on-disk DD version
            new_path = nbc_map.ctxpath[path]
            timebase = nbc_map.tbp[path]
        elif nbc_map and path in nbc_map.type_change:
            continue  # we don't handle type changes when converting implicitly
        else:
            new_path = child_meta._ctx_path
            timebase = child_meta.timebasepath

        # Override time base for homogeneous time
        if timebase and time_mode == IDS_TIME_MODE_HOMOGENEOUS:
            timebase = "/time"

        if data_type is IDSDataType.STRUCT_ARRAY:
            # Regular get/get_slice:
            with ctx.arraystruct_action(new_path, timebase, 0) as (new_ctx, size):
                if size > 0:
                    element = getattr(structure, name)
                    element.resize(size)
                    for item in element:
                        get_children(item, new_ctx, time_mode, nbc_map)
                        new_ctx.iterate_over_arraystruct(1)

        elif data_type is IDSDataType.STRUCTURE:
            element = getattr(structure, name)
            get_children(element, ctx, time_mode, nbc_map)

        else:  # Data elements
            ndim = child_meta._al_ndim
            data = ctx.read_data(new_path, timebase, data_type.al_type, ndim)
            if not (
                # Empty arrays and STR_1D
                data is None
                # EMPTY_INT, EMPTY_FLOAT, EMPTY_COMPLEX, empty string
                or (child_meta.ndim == 0 and data == data_type.default)
            ):
                # NOTE: bypassing IDSPrimitive.value.setter logic
                getattr(structure, name)._IDSPrimitive__value = data


def _get_child(child: IDSBase, ctx: Optional[LazyALContext]):
    """Get a single child when required (lazy loading)."""
    # NOTE: changes in this method must be propagated to _get_children and vice versa
    #   Performance: this method is specialized for the lazy get

    # ctx can be None when the parent structure does not exist in the on-disk DD version
    if ctx is None:
        return  # There is no data to be loaded

    time_mode = ctx.time_mode
    if time_mode == IDS_TIME_MODE_INDEPENDENT and child.metadata.type.is_dynamic:
        return  # skip dynamic (time-dependent) nodes

    child_meta = child.metadata
    path = child_meta.path_string
    data_type = child_meta.data_type
    nbc_map = ctx.nbc_map

    if nbc_map and path in nbc_map:
        if nbc_map.path[path] is None:
            return  # element does not exist in the on-disk DD version
        new_path = nbc_map.ctxpath[path]
        timebase = nbc_map.tbp[path]
    elif nbc_map and path in nbc_map.type_change:
        return  # we don't handle type changes when converting implicitly
    else:
        new_path = child_meta._ctx_path
        timebase = child_meta.timebasepath

    # Override time base for homogeneous time
    if timebase and time_mode == IDS_TIME_MODE_HOMOGENEOUS:
        timebase = "/time"

    if data_type is IDSDataType.STRUCT_ARRAY:
        aos_ctx = ctx.arraystruct_action(new_path, timebase, 0)
        child._set_lazy_context(aos_ctx)

    elif data_type is IDSDataType.STRUCTURE:
        child._set_lazy_context(ctx)

    else:  # Data elements
        ndim = child_meta._al_ndim
        data = ctx.get_context().read_data(new_path, timebase, data_type.al_type, ndim)
        if not (
            # Empty arrays and STR_1D
            data is None
            # EMPTY_INT, EMPTY_FLOAT, EMPTY_COMPLEX, empty string
            or (child_meta.ndim == 0 and data == data_type.default)
        ):
            if isinstance(data, np.ndarray):
                # Convert the numpy array to a read-only view
                data = data.view()
                data.flags.writeable = False
            # NOTE: bypassing IDSPrimitive.value.setter logic
            child._IDSPrimitive__value = data


def delete_children(structure: IDSMetadata, ctx: ALContext) -> None:
    """Recursively delete all children of an IDSStructure"""
    for child_meta in structure._children.values():
        if child_meta.data_type is IDSDataType.STRUCTURE:
            delete_children(child_meta, ctx)
        else:
            ctx.delete_data(child_meta._ctx_path)


def put_children(
    structure: IDSStructure,
    ctx: ALContext,
    time_mode: int,
    is_slice: bool,
    nbc_map: Optional[NBCPathMap],
    verify_maxoccur: bool,
) -> None:
    """Recursively put all children of an IDSStructure"""
    # Note: when putting a slice, we do not need to descend into IDSStructure and
    # IDSStructArray elements if they don't contain dynamic data nodes. That is hard to
    # detect now, so we just recurse and check the data elements
    for element in structure.iter_nonempty_():
        if time_mode == IDS_TIME_MODE_INDEPENDENT and element.metadata.type.is_dynamic:
            continue  # skip dynamic data when in time independent mode

        path = element.metadata.path_string
        if nbc_map and path in nbc_map:
            if nbc_map.path[path] is None:
                continue  # element does not exist in the on-disk DD version
            new_path = nbc_map.ctxpath[path]
            timebase = nbc_map.tbp[path]
        elif nbc_map and path in nbc_map.type_change:
            continue  # we don't handle type changes when converting implicitly
        else:
            new_path = element.metadata._ctx_path
            timebase = element.metadata.timebasepath

        # Override time base for homogeneous time
        if timebase and time_mode == IDS_TIME_MODE_HOMOGENEOUS:
            timebase = "/time"

        if isinstance(element, IDSStructArray):
            size = len(element)
            if verify_maxoccur:
                maxoccur = element.metadata.maxoccur
                if maxoccur and size > maxoccur:
                    raise RuntimeError(
                        f"Exceeding maximum number of occurrences ({maxoccur}) "
                        f"of {element._path}"
                    )
            with ctx.arraystruct_action(new_path, timebase, size) as (new_ctx, _):
                for item in element:
                    put_children(
                        item, new_ctx, time_mode, is_slice, nbc_map, verify_maxoccur
                    )
                    new_ctx.iterate_over_arraystruct(1)

        elif isinstance(element, IDSStructure):
            put_children(element, ctx, time_mode, is_slice, nbc_map, verify_maxoccur)

        else:  # Data elements
            if is_slice and not element.metadata.type.is_dynamic:
                continue  # put_slice only stores dynamic data
            ctx.write_data(new_path, timebase, element.value)
