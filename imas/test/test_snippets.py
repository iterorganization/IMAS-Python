import os
import runpy
from pathlib import Path

import pytest

courses = Path(__file__, "../../../", "docs/source/courses").resolve()
course_snippets = []
for course in ["basic", "advanced"]:
    course_snippets.extend((courses / course).glob("*snippets/*.py"))


@pytest.mark.skip(reason="skipping hli test")
@pytest.mark.filterwarnings("ignore:The input coordinates to pcolormesh:UserWarning")
@pytest.mark.parametrize("snippet", course_snippets)
def test_script_execution(snippet, monkeypatch, tmp_path, requires_imas):
    monkeypatch.chdir(tmp_path)
    # Prevent showing plots in a GUI
    monkeypatch.delenv("DISPLAY", raising=False)
    if "IMAS_HOME" not in os.environ:
        # Only execute those snippets that don't need access to the public IMAS DB
        script_text = snippet.read_text()
        if '"public"' in script_text:  # ugly hack :(
            pytest.skip("Snippet requires the public IMAS DB, which is not available")
    runpy.run_path(str(snippet))
