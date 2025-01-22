# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Helper functions to build IDSDef.xml"""

import logging
import os
import shutil
from pathlib import Path
from typing import Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from packaging.version import Version as V
from saxonche import PySaxonProcessor

logger = logging.getLogger(__name__)

_idsdef_zip_relpath = Path("imas/assets/IDSDef.zip")
_build_dir = Path("build")


def prepare_data_dictionaries():
    """Build IMAS IDSDef.xml files for each tagged version in the DD repository
    1. Use saxonche for transformations
    2. Clone the DD repository (ask for user/pass unless ssh key access is available)
    3. Generate IDSDef.xml and rename to IDSDef_${version}.xml
    4. Zip all these IDSDefs together and include in wheel
    """
    from git import Repo

    repo: Repo = get_data_dictionary_repo()
    if repo:
        newest_version_and_tag = (V("0"), None)
        for tag in repo.tags:
            version_and_tag = (V(str(tag)), tag)
            if V(str(tag)) > V("3.21.1"):
                newest_version_and_tag = max(newest_version_and_tag, version_and_tag)
                logger.debug("Building data dictionary version %s", tag)
                build_data_dictionary(repo, tag)

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

    # Set up a bare repo and fetch the data-dictionary repository in it
    os.makedirs(dd_repo_path, exist_ok=True)
    try:
        repo = git.Repo(dd_repo_path)
    except git.exc.InvalidGitRepositoryError:
        repo = git.Repo.init(dd_repo_path)
    logger.info("Set up local git repository {!s}".format(repo))

    try:
        origin = repo.remote()
    except ValueError:
        dd_repo_url = "https://github.com/iterorganization/imas-data-dictionary.git"
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


def _run_xsl_transformation(
    xsd_file: Path, xsl_file: Path, tag: str, output_file: Path
) -> None:
    """
    This function performs an XSL transformation using Saxon-HE (saxonche)
    with the provided XSD file,  XSL file, tag, and output file.

    Args:
        xsd_file (Path): XML Schema Definition (XSD) file
        xsl_file (Path): The `xsl_file` parameter
        tag (str): tag name to provide to 'DD_GIT_DESCRIBE' parameter
        output_file (Path): The `output_file` parameter for resulting xml
    """
    with PySaxonProcessor(license=False) as proc:
        logger.debug("Initializing Saxon Processor")
        xsltproc = proc.new_xslt30_processor()
        xdm_ddgit = proc.make_string_value(tag)
        xsltproc.set_parameter("DD_GIT_DESCRIBE", xdm_ddgit)
        xsltproc.transform_to_file(
            source_file=str(xsd_file),
            stylesheet_file=str(xsl_file),
            output_file=str(output_file),
        )
        logger.info("Transformation complete: %s -> %s", xsd_file, output_file)


def build_data_dictionary(repo, tag: str, rebuild=False) -> None:
    """Build a single version of the data dictionary given by the tag argument
    if the IDS does not already exist.

    In the data-dictionary repository sometimes IDSDef.xml is stored
    directly, in which case we do not call make.

    Args:
        repo: Repository object containing the DD source code
        tag: The DD version tag that will be build
        rebuild: If true, overwrites existing pre-build tagged DD version
    """
    _build_dir.mkdir(exist_ok=True)
    result_xml = _build_dir / f"{tag}.xml"

    if result_xml.exists() and not rebuild:
        logger.debug(f"XML for tag '{tag}' already exists, skipping")
        return

    repo.git.checkout(tag, force=True)

    # Perform the XSL transformation with saxonche
    dd_xsd = Path("data-dictionary/dd_data_dictionary.xml.xsd")
    dd_xsl = Path("data-dictionary/dd_data_dictionary.xml.xsl")
    _run_xsl_transformation(dd_xsd, dd_xsl, tag.name, result_xml)


if __name__ == "__main__":
    prepare_data_dictionaries()
