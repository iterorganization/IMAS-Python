import pytest

from imas import dd_zip, ids_metadata
from imas.ids_factory import IDSFactory


@pytest.fixture
def skip_object_caches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dd_zip, "_load_etree", dd_zip._load_etree.__wrapped__)
    monkeypatch.setattr(
        ids_metadata,
        "get_toplevel_metadata",
        ids_metadata.get_toplevel_metadata.__wrapped__,
    )


@pytest.fixture(params=dd_zip.dd_xml_versions())
def dd_version(request):
    return request.param


@pytest.mark.slow
def test_create_ids_dd_version(dd_version, skip_object_caches):
    # Test creation of all IDSs, test that IDSMetadata is correctly instantiated for
    # all known DD verions
    factory = IDSFactory(version=dd_version)
    for ids_name in factory:
        factory.new(ids_name)
