# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Utility class to time different sections of a CLI app."""

import time
from contextlib import contextmanager

from rich.align import Align
from rich.table import Table


class Timer:
    """Convenience class to time sections in a CLI app.

    Usage:

    .. code-block:: python

        # Construct a timer with column/row labels "X" and "Y"
        timer = Timer("X", "Y")

        # Time code
        with timer("x-value1", "y-value1"):
            ...  # Code to be timed

        # Output table with timing information
        rich.print(timer.get_table())
    """

    def __init__(self, *axes):
        self.axes = axes
        self.axes_values = tuple({} for _ in axes)
        self.data = {}

    @contextmanager
    def __call__(self, *items):
        assert len(items) == len(self.axes)
        tic = time.time()
        yield
        self.data[items] = time.time() - tic
        for i, item in enumerate(items):
            # Use dict to keep insertion order
            self.axes_values[i][item] = None

    def get_table(self, title="Timings") -> Table:
        """Construct a table with timing details.

        Currently only implemented when timing on two axes.
        """
        if len(self.axes) == 2:
            table = Table(title=title, show_footer=True)

            # Calculate totals per column
            totals = {value: 0 for value in self.axes_values[0]}
            for (col, _), value in self.data.items():
                totals[col] += value

            # Create columns
            table.add_column(footer="TOTAL:", justify="right")
            for value in self.axes_values[0]:
                table.add_column(
                    header=Align(value, "center"),
                    footer=f"{totals[value]:.3f} s",
                    justify="right",
                )

            # Fill table
            for row in self.axes_values[1]:
                row_values = (
                    f"{self.data[col, row]:.3f} s" if (col, row) in self.data else "-"
                    for col in self.axes_values[0]
                )
                table.add_row(row, *row_values)

            return table
        # non-2D is not implemented
        raise NotImplementedError()
