"""Every key the manifest emits must be described in the manual.

Documentation drift is the failure mode this repository keeps hitting: a field
is added to run.json, the manual is not touched, and a reader is left to guess
what a column means. Checking it here makes adding an undocumented field a test
failure instead of an archaeology problem later.

The check is deliberately one-directional and loose about formatting: it asserts
that each emitted key appears somewhere in the manual's manifest section, not
that the prose says anything in particular about it.
"""

import contextlib
import io
import json
import os
import re

import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline

CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")
MANUAL = os.path.join(os.path.dirname(__file__), "..", "docs", "manual",
                      "radcoolpv_manual.tex")

pytestmark = pytest.mark.skipif(not os.path.isfile(MANUAL),
                                reason="manual source not present")


def _manifest_section() -> str:
    tex = open(MANUAL).read()
    start = tex.index(r"The \code{run.json} manifest")
    end = tex.index(r"\section{Validation evidence}")
    return tex[start:end]


def _documented_names(section: str) -> set:
    return {m.replace("\\_", "_")
            for m in re.findall(r"\\code\{([A-Za-z0-9\\_]+)\}", section)}


def _run(tmp_path, config_name):
    cfg = cm.load(os.path.join(CONFIGS, config_name))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.plots = False
    cfg.run.write_outputs = True
    with contextlib.redirect_stdout(io.StringIO()):
        ctx = pipeline.run(cfg)
    return json.load(open(os.path.join(ctx.results_dir, "run.json")))


def test_every_run_json_key_appears_in_the_manual(tmp_path):
    record = _run(tmp_path, "freeform.yaml")
    emitted = (set(record)
               | set(record["thermal_results"])
               | set(record["band_averages_percent"])
               | set(record["provenance"])
               | set(record["optics"]))
    documented = _documented_names(_manifest_section())
    undocumented = sorted(k for k in emitted if k not in documented)
    assert not undocumented, (
        "run.json emits keys the manual does not mention: "
        f"{undocumented}. Add them to the manifest section of "
        "docs/manual/radcoolpv_manual.tex.")


def test_manifest_section_documents_the_top_level_shape(tmp_path):
    record = _run(tmp_path, "freeform.yaml")
    assert set(record) == {"resolved_config", "provenance", "optics",
                           "thermal_results", "band_averages_percent"}
