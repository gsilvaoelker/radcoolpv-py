"""The notebooks are the interface students actually use.

Every YAML they write is a real config against the current schema, so a schema
change that breaks one must fail here rather than in a classroom.
"""

import glob
import json
import os

import pytest

from radcoolpv import config as cm

NOTEBOOKS = sorted(glob.glob(os.path.join(
    os.path.dirname(__file__), "..", "docs", "site", "notebooks", "*.ipynb")))
ROOT = os.path.join(os.path.dirname(__file__), "..")


def _written_yaml(path):
    """Every ``%%writefile <name>.yaml`` cell as (name, body)."""
    for cell in json.load(open(path))["cells"]:
        source = "".join(cell["source"])
        if source.startswith("%%writefile ") and ".yaml" in source.split("\n", 1)[0]:
            yield source.split()[1], source.split("\n", 1)[1]


def test_the_expected_notebooks_exist():
    assert {os.path.basename(p) for p in NOTEBOOKS} == {
        "radcoolpv_colab.ipynb", "validation_a_optics.ipynb",
        "validation_b_cooling.ipynb", "validation_c_pv.ipynb",
    }


@pytest.mark.parametrize("path", NOTEBOOKS, ids=os.path.basename)
def test_every_editable_yaml_validates(path, tmp_path, monkeypatch):
    written = dict(_written_yaml(path))
    assert written, f"{os.path.basename(path)} has no editable YAML cell"
    # The notebooks chdir to the repository root, so their relative data paths
    # resolve from there.
    monkeypatch.chdir(ROOT)
    for name, body in written.items():
        target = tmp_path / name
        target.write_text(body)
        cases = cm.load_cases(str(target))
        assert len(cases) == 1, f"{name} should hold exactly one case"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=os.path.basename)
def test_every_notebook_reports_through_the_shared_helper(path):
    """Four private copies of the reporting code is how they drift apart."""
    text = open(path).read()
    assert "report.summary(" in text


def _cells(path, kind):
    return ["".join(c["source"]) for c in json.load(open(path))["cells"]
            if c["cell_type"] == kind]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=os.path.basename)
def test_the_upload_cell_matches_what_the_notebook_actually_reads(path):
    """A notebook that computes its own optics has no optics_results to set.

    The upload cell was once shared verbatim across all four notebooks, so the
    two solver-driven ones told students their spectrum was "ready to use as
    optics_results" -- a key absent from the config on the screen above it.
    """
    yaml = "\n".join(body for _, body in _written_yaml(path))
    upload = "\n".join(c for c in _cells(path, "code")
                       if c.lstrip().startswith("from google.colab"))
    assert upload, "every notebook should offer an upload cell"

    # Each notebook is one or the other: it either computes its optics from a
    # geometry and a materials block, or it reads a stored spectrum.
    assert ("optics_results:" in yaml) != ("materials:" in yaml)

    assert ("optics_results" in upload) == ("optics_results:" in yaml), (
        "the upload cell offers optics_results but the YAML never reads one"
        if "optics_results" in upload else
        "the YAML reads optics_results but the upload cell never offers it")

    installs_a_material = "materials\" / \"data" in upload or "MATERIALS" in upload
    assert installs_a_material == ("materials:" in yaml), (
        "the upload cell installs a material the YAML can never reference"
        if installs_a_material else
        "the YAML has a materials block but the upload cell cannot fill it")
