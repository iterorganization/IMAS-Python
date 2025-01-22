# pylint: disable=wrong-import-position
# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""
Packaging settings. Inspired by a minimal setup.py file, the Pandas cython build
and the access-layer setup template.

The installable imas-python package tries to follow in the following order:
- The style guide for Python code [PEP8](https://www.python.org/dev/peps/pep-0008/)
- The [PyPA guide on packaging projects](
  https://packaging.python.org/guides/distributing-packages-using-setuptools/#distributing-packages)
- The [PyPA tool recommendations](
  https://packaging.python.org/guides/tool-recommendations/), specifically:
  * Installing: [pip](https://pip.pypa.io/en/stable/)
  * Environment management: [venv](https://docs.python.org/3/library/venv.html)
  * Dependency management: [pip-tools](https://github.com/jazzband/pip-tools)
  * Packaging source distributions: [setuptools](https://setuptools.readthedocs.io/)
  * Packaging built distributions: [wheels](https://pythonwheels.com/)

On the ITER cluster we handle the environment by using the `IMAS` module load.
So instead, we install packages to the `USER_SITE` there, and do not use
`pip`s `build-isolation`. See [IMAS-584](https://jira.iter.org/browse/IMAS-584)
"""
import importlib
import importlib.util
import site
import traceback
# Allow importing local files, see https://snarky.ca/what-the-heck-is-pyproject-toml/
import sys
import warnings
# Import other stdlib packages
from pathlib import Path

# Use setuptools to build packages. Advised to import setuptools before distutils
import setuptools
from packaging.version import Version as V
from setuptools import __version__ as setuptools_version
from setuptools import setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None

# Ensure the current folder is on the import path:
sys.path.append(str(Path(__file__).parent.resolve()))

cannonical_python_command = "module load Python/3.8.6-GCCcore-10.2.0"

if sys.version_info < (3, 7):
    sys.exit(
        "Sorry, Python < 3.7 is not supported. Use a different"
        f" python e.g. '{cannonical_python_command}'"
    )
if sys.version_info < (3, 8):
    warnings.warn("Python < 3.8 support on best-effort basis", FutureWarning)


# Check setuptools version before continuing for legacy builds
# Version 61 is required for pyproject.toml support
if V(setuptools_version) < V("61"):
    raise RuntimeError(
        "Setuptools version outdated. Found"
        f" {V(setuptools_version)} need at least {V('61')}"
    )

# Workaround for https://github.com/pypa/pip/issues/7953
# Cannot install into user site directory with editable source
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]


# We need to know where we are for many things
this_file = Path(__file__)
this_dir = this_file.parent.resolve()

# Start: Load dd_helpers
dd_helpers_file = this_dir / "imas/dd_helpers.py"
assert dd_helpers_file.is_file()
spec = importlib.util.spec_from_file_location("dd_helpers", dd_helpers_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules["imas.dd_helpers"] = module
from imas.dd_helpers import prepare_data_dictionaries  # noqa

# End: Load dd_helpers


# Define building of the Data Dictionary as custom build step
class BuildDDCommand(setuptools.Command):
    """A custom command to build the data dictionaries."""

    description = "build IDSDef.zip"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Prepare DDs if they can be git pulled"""
        prepare_data_dictionaries()


# Inject prepare_data_dictionaries() into the setuptool's build steps. So far it covers
# all installation cases:
# - `pip install -e .`` (from git clone)
# - `python -m build``
# - Source tarball from git-archive. Note: version only picked up when doing git-archive
#   from a tagged release, 
#   `git archive HEAD -v -o imas.tar.gz && pip install imas.tar.gz`
cmd_class = {}
build_overrides = {"build_ext": build_ext, "build_py": build_py, "sdist": sdist}
if bdist_wheel:
    build_overrides["bdist_wheel"] = bdist_wheel
for name, cls in build_overrides.items():

    class build_DD_before(cls):
        """Build DD before executing original distutils command"""

        def run(self):
            try:
                prepare_data_dictionaries()
            except Exception:
                traceback.print_exc()
                print("Failed to build DD during setup, continuing without.")
            super().run()

    cmd_class[name] = build_DD_before


if __name__ == "__main__":
    setup(
        zip_safe=False,  # https://mypy.readthedocs.io/en/latest/installed_packages.html
        cmdclass={"build_DD": BuildDDCommand, **cmd_class}
    )