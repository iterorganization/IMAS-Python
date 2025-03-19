# A minimal testcase loading an IDS file and checking that the structure built is ok

from imas.ids_factory import IDSFactory


def test_load_minimal(ids_minimal):
    minimal = IDSFactory(xml_path=ids_minimal).new("minimal")

    # Check if the datatypes are loaded correctly
    assert minimal.a.data_type == "FLT_0D"
    assert minimal.ids_properties.comment.data_type == "STR_0D"

    # Check the documentation
    assert minimal.a.metadata.documentation == "A float"
    assert minimal.ids_properties.metadata.documentation == "Properties of this IDS"
    assert minimal.ids_properties.comment.metadata.documentation == "A string comment"

    # Check the units
    assert minimal.a.metadata.units == "unitless"

    # Check the static/dynamic/constant annotation
    assert minimal.a.metadata.type.value == "static"
    assert minimal.ids_properties.comment.metadata.type.value == "constant"


def test_load_multiple_minimal(ids_minimal, ids_minimal_types):
    minimal = IDSFactory(xml_path=ids_minimal).new("minimal")

    # Check if the datatypes are loaded correctly
    assert minimal.a.data_type == "FLT_0D"
    assert minimal.ids_properties.comment.data_type == "STR_0D"

    minimal2 = IDSFactory(xml_path=ids_minimal_types).new("minimal")

    # Check if the datatypes are loaded correctly
    assert minimal2.flt_0d.data_type == "FLT_0D"
    assert minimal2.ids_properties.comment.data_type == "STR_0D"
