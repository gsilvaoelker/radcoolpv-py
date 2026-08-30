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
def test_run_all_never_blocks_or_builds(path):
    """Runtime -> Run all has to finish on its own.

    build_s4() was once called unconditionally in A and C, so Run all spent ten
    minutes compiling before anything happened; files.upload() was called
    unconditionally in every notebook, so Run all stopped on a file picker and
    never finished at all. Both must sit behind a switch the notebook ships as
    False, in the same cell, so the default path touches neither.
    """
    for cell in _cells(path, "code"):
        for call, switch in (("files.upload()", "MY_DATA"),
                             ("build_s4()", "RECOMPUTE_WITH_S4")):
            # Match the call, not the `def` that introduces it.
            called = [ln for ln in cell.splitlines()
                      if call in ln and not ln.lstrip().startswith("def ")]
            if not called:
                continue
            assert f"{switch} = False" in cell, (
                f"{call} runs without {switch} = False in the same cell")
            before, _, after = cell.partition(f"if {switch}:")
            assert after, f"{call} is not guarded by `if {switch}:`"
            assert all(ln in after for ln in called), (
                f"{call} also runs outside `if {switch}:`")


#: Which shipped case each validation notebook must agree with.
SHIPPED = {"validation_a_optics.ipynb": "A3_optics_cylinders",
           "validation_b_cooling.ipynb": "B3_cooling_h6_cylinders",
           "validation_c_pv.ipynb": "C3_pv_cylinders"}

#: Bookkeeping that is free to differ; everything else is physics.
_IGNORED = {"results_dir", "optics_export", "plots", "write_outputs"}


def _same_file(cfg_a, value_a, cfg_b, value_b):
    """True when two configs name the same file by different relative paths."""
    if value_a is None or value_b is None:
        return value_a == value_b
    return (os.path.realpath(cfg_a.resolve_data(value_a))
            == os.path.realpath(cfg_b.resolve_data(value_b)))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=os.path.basename)
def test_notebook_yaml_matches_the_shipped_case(path, tmp_path, monkeypatch):
    """A reduced grid stops a notebook reproducing the table it prints.

    The notebooks once wrote n=60/s4_modes=20 copies of cases the shipped file
    runs at 281/60, so "Validation A" printed 0.9829 against the 0.984 its own
    introduction quotes.
    """
    case_name = SHIPPED.get(os.path.basename(path))
    if case_name is None:
        pytest.skip("not a validation notebook")
    monkeypatch.chdir(ROOT)

    (name, body), = _written_yaml(path)
    target = tmp_path / name
    target.write_text(body)
    written = cm.load_cases(str(target))[0]
    # %%writefile drops the file in the working directory, which the setup cell
    # has made the repository root; relative data paths resolve from there.
    written.base_dir = ROOT
    shipped = {c.case_name: c for c in cm.load_cases(
        os.path.join(ROOT, "validation", "akerboom.yaml"))}[case_name]

    assert written.simulation == shipped.simulation
    assert written.geometry == shipped.geometry
    assert written.structure == shipped.structure
    assert written.materials == shipped.materials

    # Path-valued keys are written relative to the file that holds them, and
    # the notebook copy sits at the repository root rather than in validation/.
    # They must name the same file, not the same string.
    for block in ("run", "thermal"):
        for field, value in vars(getattr(written, block)).items():
            if field in _IGNORED:
                continue
            other = getattr(getattr(shipped, block), field)
            if isinstance(value, str) and (value.endswith(".txt")
                                           or value.endswith(".csv")):
                assert _same_file(written, value, shipped, other), (
                    f"{block}.{field} names a different file")
            else:
                assert value == other, f"{block}.{field} differs"
