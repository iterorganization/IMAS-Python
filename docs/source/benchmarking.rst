.. _`benchmarking IMAS-Python`:

Benchmarking IMAS-Python
========================

IMAS-Python integrates with the `airspeed velocity
<https://asv.readthedocs.io/en/stable/index.html>`_ ``asv`` package for benchmarking.


IMAS-Python benchmarks
----------------------

IMAS-Python benchmarks are stored in the ``benchmarks`` folder in the git repository. We can
currently distinguish three types of benchmarks:

Technical benchmarks
    These are for benchmarking features not directly connected to user-interfacing
    functionality. For example benchmarking the time it takes to import the imas
    package.

Basic functional benchmarks
    These are for benchmarking functionality with an addition to track the performance 
    of the IMAS-Python features over time.

    For example: putting and getting IDSs.

IMAS-Python-specific functional benchmarks
    These are for benchmarking core functionalities for checking performance. We use these 
    for tracking the IMAS-Python core features performance over time.

    For example: data conversion between DD versions.


Running benchmarks (quick)
--------------------------

When you have an existing IMAS-Python development installation, you can run the benchmarks like this:

.. code-block:: console

    $ asv run --python=same --quick

.. note:: You need to have ``asv`` installed for this to work, see https://asv.readthedocs.io/en/stable/installing.html

This will execute all benchmarks once in your active python environment. The upside of
executing all benchmarks once is that this won't take very long. The downside is that
``asv`` won't be able to gather statistics (variance) of the run times, so you'll note
that in the output all timings are reported ``±0ms``.

When you remove the ``--quick`` argument, ``asv`` will execute each benchmark multiple
times. This will take longer to execute, but it also gives better statistics.


Interpreting the output
'''''''''''''''''''''''

``asv`` will output the timings of the various benchmarks. Some benchmarks are
parametrized (they are repeated with varying parameters), in which case the output
contains tabular results. Some examples:

.. code-block:: text
    :caption: Example output for a test 

    [56.25%] ··· core_profiles.Generate.time_create_core_profiles                                                                                  ok
    [56.25%] ··· ====== =============
                hli                
                ------ -------------
                imas   2.04±0.01μs 
                ====== =============


Here we see the benchmark ``core_profiles.Generate.time_create_core_profiles``.

Some benchmarks are parametrized in multiple dimensions, as in below example. This
results in a 2D table of results.

.. code-block:: text
    :caption: Example output for a test parametrized in ``backend``

    [65.62%] ··· core_profiles.Get.time_get     ok
    [65.62%] ··· ====== ========= ========== ============ ========= ============
                --                             backend                         
                ------ --------------------------------------------------------
                hli      HDF5    MDSplus      memory      ASCII      netCDF   
                ====== ========= ========== ============ ========= ============
                imas   172±3ms   86.7±2ms   68.5±0.8ms   291±3ms   14.2±0.7ms 
                ====== ========= ========== ============ ========= ============

.. note::
    The backends are listed by their numerical IDS:

    - 11: ASCII backend
    - 12: MDSplus backend
    - 13: HDF5 backend
    - 14: Memory backend


Running benchmarks (advanced)
-----------------------------

Running benchmarks quickly, as explained in the previous section, is great during
development and for comparing the performance of IMAS-Python. However,
``asv`` can also track the performance of benchmarks over various commits of IMAS-Python.
Unfortunately this is a bit more tricky to set up.


Setup advanced benchmarking
'''''''''''''''''''''''''''

First, some background on how ``asv`` tracks performance: it creates an isolated virtual
environment (using the ``virtualenv`` package) and installs IMAS-Python for each commit that
will be benchmarked. 

Deciding which commits to benchmark
'''''''''''''''''''''''''''''''''''

``asv run`` by default runs the benchmarks on two commits: the last commit on the
``main`` branch and the last commit on the ``develop`` branch. If this is what you want,
then you may skip this section and continue to the next.

If you want to customize which commits are benchmarked, then ``asv run`` allows you to
specify which commits you want to benchmark: ``asv run <range>``. The ``<range>``
argument is passed to ``git rev-list``, and all commits returned by ``git`` will be
benchmarked. See the `asv documentation for some examples
<https://asv.readthedocs.io/en/stable/using.html#benchmarking>`_.

.. caution::

    Some arguments may result in lots of commits to benchmark, for example ``asv run
    <branchname>`` will run benchmarks not only for the last commit in the branch, but
    also for every ancestor commit of it. Use ``asv run <branchname>^!`` to run a
    benchmark on just the last commit of the branch.

    It is therefore highly adviced to check the output ``git rev-list`` before running
    ``asv run``.

.. seealso:: https://asv.readthedocs.io/en/stable/commands.html#asv-run


Running benchmarks on a cluster
'''''''''''''''''''''''''''''''

For running the benchmarks on a cluster by submitting a job with SLURM, you can
adapt the following scripts to your own needs.

.. code-block:: bash
    :caption: SLURM control script (``slurm.sh``)

    #!/bin/bash

    # Set SLURM options:
    #SBATCH --job-name=IMAS-Python-benchmark
    #SBATCH --time=1:00:00
    #SBATCH --partition=<...>
    # Note: for proper benchmarking we need to exclusively reserve a node, even though
    # we're only using 1 CPU (most of the time)
    #SBATCH --exclusive
    #SBATCH --nodes=1

    bash -l ./run_benchmarks.sh

.. code-block:: bash
    :caption: Benchmark run script (``run_benchmarks.sh``)

    # If using environment modules (must be adapted to names of the modules in the targeted cluster)
    module purge
    module load IMAS-AL-Core 
    module load Python

    # Verify we can run python
    echo "Python version:"
    python --version

    # Activate the virtual environment which has asv installed
    . venv_imas/bin/activate

    # Setup asv machine (using default values)
    asv machine --yes

    # Run the benchmarks
    asv run -j 4 --show-stderr -a rounds=3 --interleave-rounds

Submit the batch job with ``sbatch slurm.sh``.


Viewing the results
'''''''''''''''''''

See https://asv.readthedocs.io/en/stable/using.html#viewing-the-results.
