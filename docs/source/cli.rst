.. _`imas-python Command Line tool`:

imas-python Command Line tool
=============================

imas-python comes with a command line tool: ``imas``. This allows you to execute
some tasks without writing Python code:

- ``imas convert`` can convert Data Entries (or, optionally, single IDSs from
  a Data Entry) to a different DD version. This command can also be used to
  convert IDSs between different backends.
- ``imas print`` can print the contents of an IDS to the terminal.
- ``imas version`` shows version information of imas-python.
- ``imas analyze-db`` and ``imas process-db-analysis`` analyze the contents
  of one or more Data Entries (stored in the HDF5 backend format). This tool is
  explained in more detail :ref:`below <imas-python Data Entry analysis>`.

You can get further details, including the expected command line arguments and
options, by running any tool with the ``--help`` flag. This help is also
available in the :ref:`Command line tool reference` below.


.. _`imas-python Data Entry analysis`:

imas-python Data Entry analysis
-------------------------------

The imas-python Data Entry analysis tool is a set of two command line programs:
``imas analyze-db`` and ``imas process-db-analysis``. The tool analyzes the
files from the HDF5 backend to figure out which IDSs are stored in the Data
Entry, and which fields from the Data Dictionary have any data stored. This
provides statistical data that is useful for Data Dictionary maintenance: by
knowing which data fields are used, more informed decisions can be made when
adding, changing or removing data fields.


Usage
'''''

The ``imas analyze-db`` is run first. Its output is then used by ``imas
process-db-analysis`` to provide statistics on the collected data.

.. rubric:: ``imas analyze-db``

``imas analyze-db`` analyzes Data Entries. You need to provide one or more
paths to folders where HDF5-backend IMAS data is stored.

.. note::

  This tool does not accept IMAS URIs. Instead of the IMAS URI
  ``imas:hdf5?path=/path/to/data/entry``, provide *only* the path to the data
  (``/path/to/data/entry`` in this example).
  
  Data Entries using the ``pulse/run/database/user`` queries can be located:

  1.  For public databases, the data is in the
      ``$IMAS_HOME/public/imasdb/<database>/<version>/<pulse>/<run>/`` folder.
  2.  Other user's data can be found in the
      ``<user_home>/public/imasdb/<database>/<version>/<pulse>/<run>/`` folder,
      where ``<user_home>`` is typically ``/home/<user>``.

The tool collects a small amount of metadata (see the output of ``imas
analyze-db --help`` for an overview) on top of the filled fields of IDSs.
All data (the metadata, and usage data of the provided Data Entries) is stored
in a `gzipped <https://en.wikipedia.org/wiki/Gzip>`__ `JSON
<https://en.wikipedia.org/wiki/JSON>`__ file.

By default this is output in ``imas-db-analysis.json.gz`` in the current
working directory, but this can be customized with the ``--output/-o`` option.
If the output file already exists, the existing data is retained and the
additional analysis data is *appended* to the file.

.. code-block:: bash
    :caption: Example usage of ``imas analyze-db``

    # Analyze a single data entry, output to the default imas-db-analysis.json.gz
    imas analyze-db /work/imas/shared/imasdb/iter_scenarios/3/106015/1/

    # Analyze a single data entry, provide a custom output filename
    imas analyze-db ./test/dataset/ -o test-dataset-analysis.json.gz

    # Analyze multiple data entries, use shell globbing to select all runs
    imas analyze-db /work/imas/shared/imasdb/iter_scenarios/3/150601/*/

    # Analyze **all** HDF5 Data Entries inside a folder
    # 1.  Find all HDF5 Data Entries (by locating their master.h5 files)
    #     in the ~/public/imasdb/ folder
    # 2.  Get the directory names for each of these files
    # 3.  Pass the directories to imas analyze-db
    find ~/public/imasdb/ -name master.h5 | \
        xargs dirname | \
        xargs imas analyze-db


.. note::

  ``imas analyze-db`` only works with the HDF5 backend, because the data files
  stored by this backend allow for a fast way to check which fields in an IDS
  are filled. We use the `h5py <https://docs.h5py.org/en/stable/index.html>`__
  Python module, which needs to be available to run the tool. An error message
  instructing to install / activate ``h5py`` is provided when ``h5py`` cannot be
  loaded.

  If your data is stored in another backend than HDF5, you can use ``imas
  convert`` to convert the data to the HDF5 backend. For example:

  .. code-block:: bash

    imas convert \
        imas:mdsplus?path=/path/to/mdsplus/data 3.41.0 imas:hdf5?path=/tmp/imas-analysis


.. rubric:: ``imas process-db-analysis``

Once you have one or more output files from ``imas analyze-db``, you can
process these files with ``imas process-db-analysis``. This will:

1.  Load all analysis results from the provided files, and compare this against
    the available fields in :ref:`The default Data Dictionary version` (which
    can be tuned by explicitly setting the ``IMAS_VERSION`` environment
    variable).
2.  These results are summarized in a table, showing per IDS:

    - The number of data fields [#data_fields]_ that were filled in *any* of the
      analyzed data entries.
    - The total number of data fields [#data_fields]_ that the Data Dictionary
      defines for this IDS.
    - The percentage of fields filled.

3.  After the summary is printed to screen, you may request a detailed breakdown
    of used fields per IDS. Input the IDS name (for example ``equilibrium``) for
    which you want to see the detailed output and press *Enter*. You may
    auto-complete an IDS name by pressing the *Tab* key. When you're done, you
    can quit the program in one of the following ways:

    - Provide an empty input.
    - Enter ``exit``.
    - Keyboard interrupt: *Ctrl+C*.
    - Enter End Of File: *Ctrl+D*.

.. code-block:: bash
    :caption: Example usage for ``imas process-db-analysis``

    # Process a single analysis output
    imas process-db-analysis imas-db-analysis.json.gz

    # Process multiple outputs
    imas process-db-anlysis workflow-1.json.gz workflow-2.json.gz

.. [#data_fields] Data fields are all fields in an IDS that can contain data.
    Structures and Arrays of Structures are not included. All data types
    (``STR``, ``INT``, ``FLT`` and ``CPX``) in all dimensions (0D-6D) are
    included in these figures.


.. _`Command line tool reference`:

Command line tool reference
---------------------------

.. click:: imas.command.cli:cli
    :prog: imas
    :nested: full
 