# This file is part of IMAS-Python.
# You should have received the IMAS-Python LICENSE file with this project.
"""IMAS-Python module to support Data Dictionary identifiers."""

import logging
from enum import Enum
from typing import Iterable, List, Type
from xml.etree.ElementTree import fromstring

from imas import dd_zip

logger = logging.getLogger(__name__)


class IDSIdentifier(Enum):
    """Base class for all identifier enums."""

    def __new__(cls, value: int, description: str, aliases: list = []):
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, value: int, description: str, aliases: list = []) -> None:
        self.index = value
        """Unique index for this identifier value."""
        self.description = description
        """Description for this identifier value."""
        self.aliases = aliases
        """Alternative names for this identifier value."""

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
            # Name may be left empty, or match name or alias
            if (
                other_name == self.name
                or other_name == ""
                or other_name in self.aliases
            ):
                # Description doesn't have to match, though we will warn when it doesn't
                if other_description not in (self.description, ""):
                    logger.warning(
                        "Description of %r does not match identifier description %r",
                        other.description,
                        self.description,
                    )
                return True

            # If we get here with matching indexes but no name/alias match, warn
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
        aliases = {}
        for int_element in element.iterfind("int"):
            name = int_element.get("name")
            value = int_element.text
            description = int_element.get("description")
            # alias attribute may contain multiple comma-separated aliases
            alias_attr = int_element.get("alias", "")
            aliases = [a.strip() for a in alias_attr.split(",") if a.strip()]
            # Canonical entry: use the canonical 'name' as key
            enum_values[name] = (int(value), description, aliases)
            # Also add alias names as enum *aliases* (they become enum attributes)
            for alias in aliases:
                enum_values[alias] = (int(value), description, aliases)
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
