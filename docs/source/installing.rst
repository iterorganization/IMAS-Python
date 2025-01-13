.. _`Installing imas-python`:

Installing imas-python
======================

imas-python is a pure Python package. For full functionality of the package you need
an installation of `the IMAS Access Layer <https://imas.iter.org/>`_. See
:ref:`imas-python 5 minute introduction` for an overview of functionality which does
(not) require the IMAS Access Layer available.


imas-python modules on the ITER cluster and EuroFusion gateway
--------------------------------------------------------------

There is a `module` available on the ITER and Eurofusion Gateway clusters, so
you can run:

.. code-block:: bash

    module load imas-python

Additionally, if you wish to use the MDSPlus backend, you should load:

.. code-block:: bash

    module load MDSplus-Java/7.96.17-GCCcore-10.2.0-Java-11

If you're using a different cluster, please contact your system administrator to see
if imas-python is available (or can be made available) on the system.


Local installation
------------------

We recommend using a :external:py:mod:`venv`. Then, clone the imas-python repository
and run `pip install`:

.. code-block:: bash

    python3 -m venv ./venv
    . venv/bin/activate
    
    git clone ssh://git@github.com:iterorganization/imas-python.git
    cd imas
    pip install --upgrade pip
    pip install --upgrade wheel setuptools
    pip install .


Development installation
------------------------

For development an installation in editable mode may be more convenient, and you
will need some extra dependencies to run the test suite and build documentation.

.. code-block:: bash

    pip install -e .[test,docs]

Test your installation by trying

.. code-block:: bash

    cd ~
    python -c "import imas; print(imas.__version__)"

This is how to run the imas-python test suite:

.. code-block:: bash

    # inside the imas-python git repository
    pytest imas --mini

    # run with a specific backend
    pytest imas --ascii --mini

And to build the imas-python documentation, execute:

.. code-block:: bash

    make -C docs html


Installation without ITER access
--------------------------------

The installation script tries to access the `ITER IMAS Core Data Dictionary
repository <https://github.com/iterorganization/imas-data-dictionary>`_
to fetch the latest versions. If you do not have git+ssh access there, you can
try to find this repository elsewhere, and do a ``git fetch --tags``.

Alternatively you could try to obtain an ``IDSDef.zip`` and place it in
``~/.config/imas/``.
