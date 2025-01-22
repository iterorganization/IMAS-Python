# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""imas-python module to support Data Dictionary identifiers.
"""

import logging
from enum import Enum
from typing import Iterable, List, Type
from xml.etree.ElementTree import fromstring

from imas import dd_zip

logger = logging.getLogger(__name__)


class IDSIdentifier(Enum):
    """Base class for all identifier enums."""

    def __new__(self, value: int, description: str):
        obj = object.__new__(self)
        obj._value_ = value
        return obj

    def __init__(self, value: int, description: str) -> None:
        self.index = value
        """Unique index for this identifier value."""
        self.description = description
        """Description for this identifier value."""

    def __eq__(self, other):
        if self is other:
            return True
        try:
            other_name = str(other.name)
            other_index = int(other.index)
            other_description = str(other.description)
        except (AttributeError, TypeError, ValueError):
            # Attribute doesn't exist, or failed to convert
            return NotImplemented
        # Index must match
        if other_index == self.index:
            # Name may be left empty
            if other_name == self.name or other_name == "":
                # Description doesn't have to match, though we will warn when it doesn't
                if other_description != self.description and other_description != "":
                    logger.warning(
                        "Description of %r does not match identifier description %r",
                        other.description,
                        self.description,
                    )
                return True
            else:
                logger.warning(
                    "Name %r does not match identifier name %r, but indexes are equal.",
                    other.name,
                    self.name,
                )
        return False

    @classmethod
    def _from_xml(cls, identifier_name, xml) -> Type["IDSIdentifier"]:
        element = fromstring(xml)
        enum_values = {}
        for int_element in element.iterfind("int"):
            name = int_element.get("name")
            value = int_element.text
            description = int_element.get("description")
            enum_values[name] = (int(value), description)
        # Create the enumeration
        enum = cls(
            identifier_name,
            enum_values,
            module=__name__,
            qualname=f"{__name__}.{identifier_name}",
        )
        enum.__doc__ = element.find("header").text
        return enum


class _IDSIdentifiers:
    """Support class to list and get identifier objects."""

    def __getattr__(self, name) -> Type[IDSIdentifier]:
        if name not in self.identifiers:
            raise AttributeError(f"Unknown identifier name: {name}")
        xml = dd_zip.get_identifier_xml(name)
        identifier = IDSIdentifier._from_xml(name, xml)
        setattr(self, name, identifier)
        return identifier

    def __getitem__(self, name) -> Type[IDSIdentifier]:
        if name not in self.identifiers:
            raise KeyError(f"Unknown identifier name: {name}")
        return getattr(self, name)

    def __dir__(self) -> Iterable[str]:
        return sorted(set(object.__dir__(self)).union(self.identifiers))

    @property
    def identifiers(self) -> List[str]:
        return dd_zip.dd_identifiers()


identifiers = _IDSIdentifiers()
"""Object to list and get identifiers.

Example:
    .. code-block:: python

        from imas import identifiers
        # List all identifier names
        for identifier_name in identifiers.identifiers:
            print(identifier_name)
        # Get a specific identifier
        csid = identifiers.core_source_identifier
        # Get and print information of an identifier value
        print(csid.total)
        print(csid.total.index)
        print(csid.total.description)

        # Item access is also possible
        print(identifiers["edge_source_identifier"])

.. seealso:: :ref:`Identifiers`
"""
