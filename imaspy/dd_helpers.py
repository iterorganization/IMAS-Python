# This file is part of IMASPy.
# You should have received the IMASPy LICENSE file with this project.
"""Helper functions to build IDSDef.xml"""

import logging
import os
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Sequence, Tuple, Union
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

from packaging.version import Version as V

logger = logging.getLogger(__name__)

_idsdef_zip_relpath = Path("imaspy/assets/IDSDef.zip")
_build_dir = Path("build")
_saxon_local_default_name = "saxon9he.jar"  # For pre-3.30.0 builds
_saxon_regex = "saxon((.(?!test|xqj))*).jar"  # Can be used in re.match


def prepare_data_dictionaries():
    """Build IMAS IDSDef.xml files for each tagged version in the DD repository
    1. Search for saxon or download it
    2. Clone the DD repository (ask for user/pass unless ssh key access is available)
    3. Generate IDSDef.xml and rename to IDSDef_${version}.xml
    4. Zip all these IDSDefs together and include in wheel
    """
    from git import Repo

    saxon_jar_path = get_saxon()
    repo: Repo = get_data_dictionary_repo()
    if repo:
        newest_version_and_tag = (V("0"), None)
        for tag in repo.tags:
            version_and_tag = (V(str(tag)), tag)
            if V(str(tag)) > V("3.21.1"):
                newest_version_and_tag = max(newest_version_and_tag, version_and_tag)
                logger.debug("Building data dictionary version %s", tag)
                build_data_dictionary(repo, tag, saxon_jar_path)

        logger.info("Creating zip file of DD versions")

        if _idsdef_zip_relpath.is_file():
            logger.warning("Overwriting '%s'", _idsdef_zip_relpath)

        with ZipFile(
            _idsdef_zip_relpath,
            mode="w",  # this needs w, since zip can have multiple same entries
            compression=ZIP_DEFLATED,
        ) as dd_zip:
            for filename in _build_dir.glob("[0-9]*.xml"):
                arcname = Path("data-dictionary").joinpath(*filename.parts[1:])
                dd_zip.write(filename, arcname=arcname)
            # Include identifiers from latest tag in zip file
            repo.git.checkout(newest_version_and_tag[1], force=True)
            # DD layout <= 4.0.0
            for filename in Path("data-dictionary").glob("*/*identifier.xml"):
                arcname = Path("identifiers").joinpath(*filename.parts[1:])
                dd_zip.write(filename, arcname=arcname)
            # DD layout > 4.0.0
            for filename in Path("data-dictionary").glob("schemas/*/*identifier.xml"):
                arcname = Path("identifiers").joinpath(*filename.parts[2:])
                dd_zip.write(filename, arcname=arcname)


# pre 3.30.0 versions of the DD have the `saxon9he.jar` file path hardcoded
# in their makefiles. To be sure we can build everything, we link whatever
# saxon we can find to a local file called saxon9he.jar
def get_saxon() -> Path:
    """Search for saxon*.jar and return the path or download it.
    The DD build works by having Saxon in the CLASSPATH, called saxon9he.jar
    until DD version 3.30.0. After 3.30.0 Saxon is found by the SAXONJARFILE env
    variable. We will 'cheat' a little bit later by symlinking saxon9he.jar to
    any version of saxon we found.

    Check:
    1. CLASSPATH
    2. `which saxon`
    3. /usr/share/java/*
    4. or download it
    """

    local_saxon_path = Path.cwd() / _saxon_local_default_name
    if local_saxon_path.exists():
        logger.debug("Something already at '%s' not creating anew", local_saxon_path)
        return local_saxon_path

    saxon_jar_origin = Path(
        find_saxon_classpath()
        or find_saxon_bin()
        or find_saxon_jar()
        or download_saxon()
    )
    logger.info("Found Saxon JAR '%s'", saxon_jar_origin)
    if saxon_jar_origin.name != _saxon_local_default_name:
        try:
            os.symlink(saxon_jar_origin, local_saxon_path)
        except FileExistsError:
            # Another process could have created the symlink while we were searching
            logger.debug(
                "Link '%s' exists, parallel process might've created it",
                local_saxon_path,
            )
        return local_saxon_path
    return saxon_jar_origin


def find_saxon_jar():
    # This finds multiple versions on my system, but they are symlinked together.
    # take the shortest one.
    jars = [
        path
        for path in Path("/usr/share/java").rglob("*")
        if re.match(_saxon_regex, path.name, flags=re.IGNORECASE)
    ]

    if jars:
        saxon_jar_path = min(jars, key=lambda x: len(x.parts))
        return saxon_jar_path


def find_saxon_classpath():
    """Search JAVAs CLASSPATH for a Saxon .jar"""
    classpath = os.environ.get("CLASSPATH", "")
    for part in re.split(";|:", classpath):
        if (
            part.endswith(".jar")
            and part.split("/")[-1].startswith("saxon")
            and "test" not in part
            and "xqj" not in part
        ):
            return part


def find_saxon_bin():
    """Search for a saxon executable"""
    saxon_bin = shutil.which("saxon")
    if saxon_bin:
        with open(saxon_bin, "r") as file:
            for line in file:
                saxon_jar_path = re.search("[^ ]*saxon[^ ]*jar", line)
                if saxon_jar_path:
                    return saxon_jar_path.group(0)


def download_saxon():
    """Downloads a zipfile containing Saxon and extract it to the current dir.
    Return the full path to Saxon. This can be any Saxon version. Scripts that
    wrap this should probably manipulate either the name of this file, and/or
    the CLASSPATH"""

    SAXON_PATH = "https://github.com/Saxonica/Saxon-HE/releases/download/SaxonHE10-9/SaxonHE10-9J.zip"  # noqa: E501

    resp = urlopen(SAXON_PATH, timeout=120.0)
    zipfile = ZipFile(BytesIO(resp.read()))
    # Zipfile has a list of the ZipInfos. Look inside for a Saxon jar
    for file in zipfile.filelist:
        if re.match(_saxon_regex, file.filename, flags=re.IGNORECASE):
            path = zipfile.extract(file)
            del zipfile
            return path
    raise FileNotFoundError(f"No Saxon jar found in given zipfile '{SAXON_PATH}'")


def get_data_dictionary_repo() -> Tuple[bool, bool]:
    try:
        import git  # Import git here, the user might not have it!
    except ModuleNotFoundError:
        raise RuntimeError(
            "Could not find 'git' module, try 'pip install gitpython'. \
            Will not build Data Dictionaries!"
        )

        # We need the actual source code (for now) so grab it from ITER
    dd_repo_path = "data-dictionary"

    if "DD_DIRECTORY" in os.environ:
        logger.info("Found DD_DIRECTORY, copying")
        try:
            shutil.copytree(os.environ["DD_DIRECTORY"], dd_repo_path)
        except FileExistsError:
            pass
    else:
        logger.info("Trying to pull data dictionary git repo from ITER")

    # Set up a bare repo and fetch the access-layer repository in it
    os.makedirs(dd_repo_path, exist_ok=True)
    try:
        repo = git.Repo(dd_repo_path)
    except git.exc.InvalidGitRepositoryError:
        repo = git.Repo.init(dd_repo_path)
    logger.info("Set up local git repository {!s}".format(repo))

    try:
        origin = repo.remote()
    except ValueError:
        dd_repo_url = "ssh://git@git.iter.org/imas/data-dictionary.git"
        origin = repo.create_remote("origin", url=dd_repo_url)
    logger.info("Set up remote '{!s}' linking to '{!s}'".format(origin, origin.url))

    try:
        origin.fetch(tags=True)
    except git.exc.GitCommandError as ee:
        logger.warning(
            "Could not fetch tags from %s. Git reports:\n %s." "\nTrying to continue",
            list(origin.urls),
            ee,
        )
    else:
        logger.info("Remote tags fetched")
    return repo


def _run_data_dictionary(
    args: Union[Sequence, str], tag: str, saxon_jar_path: str
) -> int:
    """Run in a Data Dictionary environment. Used e.g. to run the DD Makefile

    Args:
        args: The "args" argument directly passed to :func:`subprocess.run`,
            e.g. ``["make", "clean"]``
        tag: The DD version tag that will be printed on error
        saxon_jar_path: The path to the saxon jar; Added to CLASSPATH and used
            to generate the DD
    """
    env = os.environ.copy()
    env["CLASSPATH"] = f"{saxon_jar_path}:{env.get('CLASSPATH', '')}"
    result = subprocess.run(
        args,
        bufsize=0,
        capture_output=True,
        cwd=os.getcwd() + "/data-dictionary",
        env=env,
        text=True,
    )

    if result.returncode != 0:
        logger.warning("Error making DD version %s, make reported:", tag)
        logger.warning("CLASSPATH ='%s'", saxon_jar_path)
        logger.warning("PATH = '%s'", os.environ.get("PATH", ""))
        logger.warning("stdout = '%s'", result.stdout.strip())
        logger.warning("stderr = '%s'", result.stderr.strip())
        logger.warning("continuing without DD version %s", tag)
    else:
        logger.debug(
            "Successful make for DD %s.\n-- Make stdout --\n%s\n-- Make stderr --\n%s",
            tag,
            result.stdout,
            result.stderr,
        )
    return result.returncode


def build_data_dictionary(repo, tag: str, saxon_jar_path: str, rebuild=False) -> None:
    """Build a single version of the data dictionary given by the tag argument
    if the IDS does not already exist.

    In the data-dictionary repository sometimes IDSDef.xml is stored
    directly, in which case we do not call make.

    Args:
        repo: Repository object containing the DD source code
        tag: The DD version tag that will be build
        saxon_jar_path: The path to the saxon jar; Added to CLASSPATH and used
            to generate the DD
        rebuild: If true, overwrites existing pre-build tagged DD version
    """
    _build_dir.mkdir(exist_ok=True)
    result_xml = _build_dir / f"{tag}.xml"

    if result_xml.exists() and not rebuild:
        logger.debug(f"XML for tag '{tag}' already exists, skipping")
        return

    repo.git.checkout(tag, force=True)
    if _run_data_dictionary(["make", "clean"], tag, saxon_jar_path) != 0:
        return
    if _run_data_dictionary(["make", "IDSDef.xml"], tag, saxon_jar_path) != 0:
        return

    # copy and delete original instead of move (to follow symlink)
    IDSDef = Path("data-dictionary/IDSDef.xml")
    try:
        shutil.copy(
            IDSDef,  # Hardcoded in access-layer makefile
            result_xml,
            follow_symlinks=True,
        )
    except shutil.SameFileError:
        pass
    IDSDef.unlink(missing_ok=True)


if __name__ == "__main__":
    prepare_data_dictionaries()
