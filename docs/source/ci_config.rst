.. _`ci configuration`:

CI configuration
================

imas-python uses `ITER Bamboo <https://ci.iter.org/>`_ for CI. This page provides an overview
of the CI Plan and deployment projects.

CI Plan
-------

The `imas-python CI plan <https://ci.iter.org/browse/IC-IG>`_ consists of 4 types of jobs:

Linting and DD ZIP
    This job is responsible for three things:

    1.  Verify that the ``IDSDef2MDSplusPreTree.xsl`` file matches the one in the Access
        Layer repository. This file is required for building MDSplus models and the
        models built by imas-python should match those built by the Access Layer.
    2.  Linting: run ``black`` and ``flake8`` on the imas-python code base. See :ref:`code
        style and linting`.
    3.  Build the Data Dictionary zip file. This Task builds the Data Dictionary for all
        tagged releases since DD version ``3.22.0``. These are combined into the
        ``IDSDef.zip`` file, which is distributed with imas-python.

        The ZIP file is built in a separate job, such that the subsequent test jobs can
        reuse this.

    The CI scripts executed in this job are:

    - ``ci/linting.sh``
    - ``ci/build_dd_zip.sh``

Test with AL<version>
    This runs all unit tests with pytest.
    Access Layer version that we test against: 
    IMAS-AL-Core/5.4.3-intel-2023b

    The CI script executed in this job is ``ci/run_pytest.sh``, which expects the
    modules it needs to load as arguments.

    Cloning this job to test against a new AL version is easy:

    1.  On the "Default plan configuration" page of Bamboo, click "+ Add job" and select
        the option to "Clone an existing job".
    2.  Select one of the existing Test jobs.
    3.  Indicate the new AL version in the job name.
    4.  Click Create job
    5.  In the "Script" Task, update the module(s) in the Argument field

Benchmark
    This job runs the :ref:`ASV benchmarks <benchmarking IMAS>` on the CI server. It
    is configured such that it can only run on a single CI agent
    (`io-ls-bamboowk6.iter.org`). There are two reasons for this:

    1.  Simplify the data I/O of the script - we can avoid file locks because there will
        only be a single Benchmark Job running globally. This is the main reason.
    2.  Benchmarks should be more reproduceable when always run on the same machine.
        Although the agents are virtualized, so the performance will always depend to
        some extent to the load on the CI cluster.

    The CI script executed in this job is: ``ci/run_benchmark.sh``.

Build docs and dists
    This job builds the Sphinx documentation and python packages for imas-python (``sdist``
    and ``wheel``).

    The CI script executed in this job is: ``ci/build_docs_and_dist.sh``.


Deployment projects
-------------------

There is github workflow for imas-python:

`imas-python-PyPi <https://github.com/iterorganization/imas-python/blob/main/.github/workflows/publish.yml>`_
    Deploy the python packages job to the  https://pypi.org/ server and https://test.pypi.org/ server.
    You can find link here : `imas-python <https://pypi.org/project/imas-python/>`_


`Deploy imas-python-doc <https://app.readthedocs.org/projects/imas-python/>`_
    Deploy the documentation using `readthedocs
    <https://imas-python.readthedocs.io/en/latest/>`_.

