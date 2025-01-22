.. _`benchmarking IMAS`:

Benchmarking imas-python
========================

imas-python integrates with the `airspeed velocity
<https://asv.readthedocs.io/en/stable/index.html>`_ ``asv`` package for benchmarking.


imas-python benchmarks
----------------------

imas-python benchmarks are stored in the ``benchmarks`` folder in the git repository. We can
currently distinguish three types of benchmarks:

Technical benchmarks
    These are for benchmarking features not directly connected to user-interfacing
    functionality. For example benchmarking the time it takes to import the imas
    package.

Basic functional benchmarks
    These are for benchmarking functionality with an equivalent feature in the IMAS
    Access Layer HLI. In addition to tracking the performance of the imas-python features
    over time, we can also benchmark the performance against the traditional HLI.

    For example: putting and getting IDSs.

imas-python-specific functional benchmarks
    These are for benchmarking functionality without an equivalent feature in the IMAS
    Access Layer HLI. We use these for tracking the imas-python performance over time.

    For example: data conversion between DD versions.


Running benchmarks (quick)
--------------------------

When you have an existing imas-python installation, you can run the benchmarks like this:

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
    :caption: Example output for a test parametrized in ``hli``

    [ 58.33%] ··· core_profiles.Generate.time_create_core_profiles          ok
    [ 58.33%] ··· ======== ============
                    hli                
                  -------- ------------
                    imas    22.9±0.4μs 
                   imas    408±8μs   
                  ======== ============

Here we see the benchmark ``core_profiles.Generate.time_create_core_profiles`` was
repeated for multiple values of ``hli``: once for the ``imas`` HLI, and once for the
``imas`` HLI.

Some benchmarks are parametrized in multiple dimensions, as in below example. This
results in a 2D table of results.

.. code-block:: text
    :caption: Example output for a test parametrized in ``hli`` and ``backend``

    [ 70.83%] ··· core_profiles.Get.time_get                                ok
    [ 70.83%] ··· ======== ========== ============ =========
                  --                    backend             
                  -------- ---------------------------------
                    hli        13          14          11   
                  ======== ========== ============ =========
                    imas    75.1±1ms   70.2±0.5ms   207±2ms 
                   imas   241±4ms     229±2ms     364±6ms 
                  ======== ========== ============ =========

.. note::
    The backends are listed by their numerical IDS:

    - 11: ASCII backend
    - 12: MDSplus backend
    - 13: HDF5 backend
    - 14: Memory backend


Running benchmarks (advanced)
-----------------------------

Running benchmarks quickly, as explained in the previous section, is great during
development and for comparing the performance of imas-python against the imas HLI. However,
``asv`` can also track the performance of benchmarks over various commits of imas-python.
Unfortunately this is a bit more tricky to set up.


Setup advanced benchmarking
'''''''''''''''''''''''''''

First, some background on how ``asv`` tracks performance: it creates an isolated virtual
environment (using the ``virtualenv`` package) and installs imas-python for each commit that
will be benchmarked. However, because the virtual environment is isolated, the ``imas``
package won't be available. We need to work around it by setting the environment
variable ``ASV_PYTHONPATH``:

.. code-block:: console
    :caption: Setting up the ``ASV_PYTHONPATH`` on SDCC

    $ module load IMAS
    $ export ASV_PYTHONPATH="$PYTHONPATH"

.. caution::

    ``imas`` must not be available on the ``ASV_PYTHONPATH`` to avoid the interfering
    of two imas modules (one on the ``PYTHONPATH``, and the other installed by ``asv``
    in the virtual environment).


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


Running benchmarks on SDCC
''''''''''''''''''''''''''

Running benchmarks on the SDCC login nodes is useful for debugging, but not for
comparing performance: many people are using the login nodes at the same time, and the
machine load is variable.

Instead, you can submit a benchmark job to the compute nodes. 

.. code-block:: bash
    :caption: SLURM control script (``slurm.sh``)

    #!/bin/bash

    # Set SLURM options:
    #SBATCH --job-name=imas-python-benchmark
    #SBATCH --time=1:00:00
    #SBATCH --partition=gen10_ib
    # Note: for proper benchmarking we need to exclusively reserve a node, even though
    # we're only using 1 CPU (most of the time)
    #SBATCH --exclusive
    #SBATCH --nodes=1

    bash -l ./run_benchmarks.sh

.. code-block:: bash
    :caption: Benchmark run script (``run_benchmarks.sh``)

    # Load IMAS module
    module purge
    module load IMAS
    # Verify we can run python and import imas
    echo "Python version:"
    python --version
    echo "Import imas:"
    python -c 'import imas; print(imas)'

    # Set the ASV_PYTHONPATH so we can `import imas` in the benchmarks
    export ASV_PYTHONPATH="$PYTHONPATH"
    echo "ASV_PYTHONPATH=$ASV_PYTHONPATH"
    echo

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
