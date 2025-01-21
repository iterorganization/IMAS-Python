# Helper functions to create MDSPlus reference models
# and store them in a cache directory (.cache/imas/MDSPlus/name-HASH/)
"""Module for generating and working with MDSplus models.
"""

import errno
import getpass
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from saxonche import PySaxonProcessor
from subprocess import CalledProcessError, check_output
from zlib import crc32

try:
    from importlib.resources import as_file, files
except ImportError:  # Python 3.8 support
    from importlib_resources import as_file, files

import imas
from imas.dd_zip import get_dd_xml, get_dd_xml_crc
from imas.exception import MDSPlusModelError
from imas.ids_factory import IDSFactory

logger = logging.getLogger(__name__)


MDSPLUS_MODEL_TIMEOUT = int(os.getenv("MDSPLUS_MODEL_TIMEOUT", "120"))


def safe_replace(src: Path, dst: Path) -> None:
    """Replace a folder from ``src`` to ``dst``, overwriting `dst` if it is empty.

    *   Moves must be atomic.  ``shutil.move()`` is not atomic.
        Note that multiple threads may try to write to the cache at once,
        so atomicity is required to ensure the serving on one thread doesn't
        pick up a partially saved image from another thread.

    *   Moves must work across filesystems.  Often temp directories and the
        cache directories live on different filesystems.  ``os.replace()`` can
        throw errors if run across filesystems.

    So we try ``os.replace()``, but if we detect a cross-filesystem copy, we
    switch to ``shutil.move()`` with some wrappers to make it atomic.
    """
    # From https://alexwlchan.net/2019/03/atomic-cross-filesystem-moves-in-python/
    try:
        src.replace(dst)
    except OSError as err:
        if err.errno == errno.EXDEV:
            # Generate a unique ID, and copy `<src>` to the target directory
            # with a temporary name `<dst>.<ID>.tmp`.  Because we're copying
            # across a filesystem boundary, this initial copy may not be
            # atomic.  We intersperse a random UUID so if different processes
            # are copying into `<dst>`, they don't overlap in their tmp copies.
            copy_id = uuid.uuid4()
            tmp_dst = dst.with_name(f"{dst.name}.{copy_id}.tmp")
            shutil.copytree(src, tmp_dst)

            # Then do an atomic replace onto the new name, and clean up the source path
            try:
                tmp_dst.replace(dst)
            except OSError as err:
                # if the folder is not empty, another process beat us, ignore error
                if err.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise  # otherwise raise the error
            shutil.rmtree(src)
        elif err.errno in (errno.EEXIST, errno.ENOTEMPTY):
            # if the folder is not empty, another process beat us, ignore error
            pass
        else:
            raise


def mdsplus_model_dir(factory: IDSFactory) -> str:
    """
    when given a version number this looks for the DD definition
    of that version in the internal cache. Alternatively a filename
    can be passed, which leads us to use that XML file to build an
    MDSplus model directory.


    Given a filename and xml contents create an xml
    document for the mdsplus model by running a command like the below:

    java net.sf.saxon.Transform -s:- -xsl: -o:${OUTPUT_FILE}

    with ENV:
    env={"CLASSPATH": saxon_jar_path, "PATH": os.environ.get("PATH", "")}

    Args:
        factory: IDSFactory indicating the DD version / XML to build models for.

    Returns:
        The path to the requested DD cache
    """

    # Calculate a checksum on the contents of a DD XML file to uniquely
    # identify our cache files, and re-create them as-needed if the contents
    # of the file change

    if factory._xml_path is None:  # Factory was created from version
        version = factory.version
        crc = get_dd_xml_crc(version)
        xml_name = version + ".xml"
        fname = "-"
    else:
        version = None
        xml_name = Path(factory._xml_path).name
        fname = factory._xml_path
        with open(fname, "rb") as file:
            crc = crc32(file.read())

    cache_dir_name = "%s-%08x" % (xml_name, crc)
    cache_dir_path = Path(_get_xdg_cache_dir()) / "imas" / "mdsplus" / cache_dir_name
    # TODO: include hash or version of "IDSDef2MDSpreTree.xsl", which we should fetch
    # from the access layer instead of provide ourselves, if we wish to be resilient to
    # upgrades there (has happened early 2021 already once). of course, upgrades to the
    # on-disk formats should be versioned and documented properly, so this should never
    # happen again.

    # There are multiple possible cases for the imas-python cache
    # 1. The cache exist and can be used
    # 2. The cache folder exists, and another process is creating it
    # 3. The cache folder exists, but the process creating it has stopped
    # 4. The cache folder does not exist and this process should make it
    #
    # As (cross)-filesystem operations can in principle collide, we use
    # a statistically unique temp dir which we move with a special safe and
    # atomic function if the generation successfully finished

    fuuid = uuid.uuid4().hex
    tmp_cache_dir_path = (
        Path(tempfile.gettempdir())
        / getpass.getuser()
        / "imas"
        / "mdsplus"
        / f"{cache_dir_name}_{fuuid}"
    )
    if cache_dir_path.is_dir() and model_exists(cache_dir_path):
        # Case 1: The model already exists on the right location, done!
        generate_tmp_cache = False
    elif cache_dir_path.is_dir() and not model_exists(cache_dir_path):
        # The cache dir has been created, but not filled: case 3 or 4.
        # We wait until it fills on its own (case 3)
        logger.warning(
            "Model dir %s exists but is empty. Waiting %ss for contents.",
            cache_dir_path,
            MDSPLUS_MODEL_TIMEOUT,
        )
        # If it timed out (case 4), we will create a new cache in this process
        generate_tmp_cache = not wait_for_model(cache_dir_path)
        # We expect cache_dir_path is empty when we need to generate
        if generate_tmp_cache and len(os.listdir(cache_dir_path)) > 1:
            if not model_exists(cache_dir_path):
                logger.debug(
                    "Model directory %s contents: %s",
                    cache_dir_path,
                    os.listdir(cache_dir_path),
                )
                raise MDSPlusModelError(
                    "The imas-python cache directory is corrupted. Please clean the"
                    f" cache directory ({cache_dir_path}) and try again."
                )
    elif not cache_dir_path.is_dir() and not model_exists(cache_dir_path):
        # The cache did not exist, we will create a new cache in this process
        generate_tmp_cache = True
    else:
        raise RuntimeError("Programmer error, this case should never be true")

    if generate_tmp_cache:
        # create the empty directory to indicate we are building a new model
        try:
            cache_dir_path.mkdir(parents=True, exist_ok=True)
            # ideally next we drop a timestamp so any successors can see how long they
            # should wait
            logger.info(
                "Creating and caching MDSplus model at %s, this may take a while",
                tmp_cache_dir_path,
            )
            create_model_ids_xml(tmp_cache_dir_path, fname, version)
            create_mdsplus_model(tmp_cache_dir_path)

            logger.info(
                "MDSplus model at %s created, moving to %s",
                tmp_cache_dir_path,
                cache_dir_path,
            )
            safe_replace(tmp_cache_dir_path, cache_dir_path)

            if not model_exists(cache_dir_path):
                raise MDSPlusModelError(
                    "Unexpected error while generating MDSPlus model cache. "
                    "Please create a bug report."
                )
        except Exception as ee:
            logger.error("Error creating MDSPlus file")
            # remove cache directory so our successor does not spend time waiting
            shutil.rmtree(cache_dir_path)
            raise ee

    return str(cache_dir_path)


def wait_for_model(cache_dir_path: Path) -> bool:
    """Wait MDSPLUS_MODEL_TIMEOUT seconds until model appears in directory

    Returns:
        True if the cache folder is found, and false if the
        wait loop timed out.
    """
    for _ in range(MDSPLUS_MODEL_TIMEOUT):
        if model_exists(cache_dir_path):
            return True
        time.sleep(1)
    else:
        logger.warning(
            "Timeout exceeded while waiting for MDSplus model, try overwriting"
        )
        return False


def model_exists(path: Path) -> bool:
    """Given a path to an IDS model definition check if all components are there"""
    return all(
        map(
            lambda f: os.path.isfile(path / f),
            [
                "ids.xml",
                "ids_model.characteristics",
                "ids_model.datafile",
                "ids_model.tree",
                "done.txt",
            ],
        )
    )


# def create_model_ids_xml(cache_dir_path, fname, version):
#     """Use saxon to compile an ids.xml suitable for creating an mdsplus model."""

#     try:
#         # we have to be careful to have the same version of this file as in the access
#         # layer:
#         with as_file(files(imas) / "assets" / "IDSDef2MDSpreTree.xsl") as xslfile:
#             check_output(
#                 [
#                     "java",
#                     "net.sf.saxon.Transform",
#                     "-s:" + str(fname),
#                     "-o:" + str(Path(cache_dir_path) / "ids.xml"),
#                     "DD_GIT_DESCRIBE=" + str(version or fname),
#                     # if this is expected as git describe it might break
#                     # if we just pass a filename
#                     "AL_GIT_DESCRIBE=" + os.environ.get("AL_VERSION", "0.0.0"),
#                     "-xsl:" + str(xslfile),
#                 ],
#                 input=get_dd_xml(version) if version else None,
#                 env={"CLASSPATH": get_saxon(), "PATH": os.environ.get("PATH", "")},
#             )
#     except CalledProcessError as e:
#         if fname:
#             logger.error("Error making MDSPlus model IDS.xml for %s", fname)
#         else:
#             logger.error("Error making MDSplus model IDS.xml for %s", version)
#         raise e


def create_model_ids_xml(cache_dir_path, fname, version):
    """Use Saxon/C to compile an ids.xml suitable for creating an MDSplus model."""
    try:
        # Locate the XSL file within the package
        with as_file(files("imas") / "assets" / "IDSDef2MDSpreTree.xsl") as xslfile:
            output_file = Path(cache_dir_path) / "ids.xml"
            
            # Initialize Saxon/C processor
            with PySaxonProcessor(license=False) as proc:
                xslt_processor = proc.new_xslt30_processor()

                # Set the XSLT stylesheet
                xslt_processor.compile_stylesheet(stylesheet_file=str(xslfile))

                # Prepare the input XML source
                input_xml = get_dd_xml(version) if version else None
                if fname:
                    source_file = str(fname)
                elif input_xml:
                    source_file = "-"  # Use standard input for the XML string
                else:
                    raise ValueError("Either 'fname' or 'version' must be provided to generate XML.")

                # xdm_ddgit = proc.make_string_value(str(version or fname))
                # xsltproc.set_parameter("DD_GIT_DESCRIBE", xdm_ddgit)
                # xdm_algit = proc.make_string_value(os.environ.get("AL_VERSION", "0.0.0"))
                # xsltproc.set_parameter("AL_GIT_DESCRIBE", xdm_algit)
                # Transform XML
                result = xslt_processor.transform_to_file(
                    source_file=source_file,
                    output_file=str(output_file),
                    initial_template_params={
                        "DD_GIT_DESCRIBE": str(version or fname),
                        "AL_GIT_DESCRIBE": os.environ.get("AL_VERSION", "0.0.0"),
                    },
                )

                if result is False:
                    logger.error("Transformation failed: Check Saxon/C logs for details.")
                    raise RuntimeError("Saxon/C XSLT transformation failed.")

    except Exception as e:
        if fname:
            logger.error("Error making MDSplus model IDS.xml for %s", fname)
        else:
            logger.error("Error making MDSplus model IDS.xml for %s", version)
        raise e
    

def create_mdsplus_model(cache_dir_path: Path) -> None:
    """Use jtraverser to compile a valid MDS model file."""
    try:
        # In newer versions of MDSplus, CompileTree is renamed to
        # mds.jtraverser.CompileTree. Find out which to use:
        jarfile = str(jTraverser_jar())
        compiletree_class = check_output(
            ["jar", "tf", jarfile, "CompileTree", "mds/jtraverser/CompileTree"]
        ).decode("utf-8")
        if not compiletree_class:
            raise MDSPlusModelError(
                f"Error making MDSplus model in {cache_dir_path}: "
                "Could not determine CompileTree class in jTraverser.jar."
            )
        compiletree = compiletree_class.rpartition(".class")[0].replace("/", ".")
        check_output(
            [
                "java",
                "-Xms1g",  # what do these do?
                "-Xmx8g",  # what do these do?
                "-XX:+UseG1GC",  # what do these do?
                "-cp",
                jarfile,
                compiletree,
                "ids",
            ],
            cwd=str(cache_dir_path),
            env={
                "PATH": os.environ.get("PATH", ""),
                "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH", ""),
                "ids_path": str(cache_dir_path),
            },
        )
        # Touch a file to show that we have finished the model
        (cache_dir_path / "done.txt").touch()
    except CalledProcessError as e:
        logger.error("Error making MDSPlus model in {path}", cache_dir_path)
        raise e


def _get_xdg_cache_dir() -> str:
    """
    Return the XDG cache directory, according to the XDG base directory spec:

    https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")


def jTraverser_jar() -> Path:
    """Search a few common locations and CLASSPATH for jTraverser.jar
    which is provided by MDSPlus."""
    search_dirs = ["/usr/share/java"]

    for component in os.environ.get("CLASSPATH", "").split(":"):
        if component.endswith(".jar"):
            if re.search(".*jTraverser.jar", component):
                return component
        else:  # assume its a directory (strip any '*' suffix)
            search_dirs.append(component.rstrip("*"))

    files = []
    for dir in search_dirs:
        files += Path(dir).rglob("*")

    jars = [path for path in files if path.name == "jTraverser.jar"]

    if jars:
        jar_path = min(jars, key=lambda x: len(x.parts))
        return jar_path
    else:
        raise MDSPlusModelError("jTraverser.jar not found. Is MDSplus-Java available?")


def ensure_data_dir(user: str, tokamak: str, version: str, run: int) -> None:
    """Ensure that a data dir exists with a similar algorithm that
    the MDSplus backend uses to set the data path.
    See also mdsplus_backend.cpp:751 (setDataEnv)"""
    if user == "public":
        if "IMAS_HOME" not in os.environ:
            raise RuntimeError(
                "Environment variable IMAS_HOME must be set to access "
                "the public database."
            )
        dbdir = Path(os.environ["IMAS_HOME"]) / "shared" / "imasdb" / tokamak / version
    elif user[0] == "/":
        dbdir = Path(user) / tokamak / version
    else:
        dbdir = Path.home() / "public" / "imasdb" / tokamak / version

    # Check subfolder based on run
    assert 0 <= run <= 99_999
    index = run // 10_000
    (dbdir / str(index)).mkdir(parents=True, exist_ok=True)
