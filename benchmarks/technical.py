import imas


def timeraw_create_default_imas_factory():
    # timeraw to ensure that nothing is cached
    return """
    import imas
    imas.IDSFactory()
    """


def timeraw_import_imas():
    return """
    import imas
    """


# It would be nice if we could track these, but unfortunately it breaks things like
# `asv compare` :(
"""
def track_imas_versions():
    ids_factory = imas.IDSFactory()
    equilibrium = ids_factory.equilibrium()
    equilibrium.ids_properties.homogeneous_time = imas.ids_defs.IDS_TIME_MODE_INDEPENDENT
    dbentry = imas.DBEntry(imas.ids_defs.MEMORY_BACKEND, "test", 1, 1)
    dbentry.create()
    dbentry.put(equilibrium)
    equilibrium = dbentry.get("equilibrium")
    return (
        equilibrium.ids_properties.version_put.data_dictionary,
        equilibrium.ids_properties.version_put.access_layer,
    )


def track_imas_dd_version():
    return imas.IDSFactory().version
"""
