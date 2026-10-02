"""Integration tests for the GitHub Pages build (issue #33).

The tests verify the website build integration
(docs/testing/test-levels.md, section 4.5):

    docs/
      +
    output/
      |
      v
    build_pages
      |
      v
    build/

and the assembly implemented by src/update/build_pages.py:

* the static website below docs/ is copied to the build root,
* the generated project output below output/ is copied to
  build/output/ -- the deployment path the website pages use
  for figures and latest.json,
* the resulting directory structure matches the GitHub Pages
  deployment structure,
* rebuilding is reproducible: a second build yields byte-
  identical files and removes stale products of a previous
  build.

Test design:

* The build stage is a pure copy step -- no analysis or
  plotting code runs -- so the controlled inputs are small
  hand-written files:
  - docs/: a compact page pair (index.html and a nested
    overview/results.html) plus a stylesheet, modeled on the
    production website structure; like the real pages they
    reference plots through "output/plots/..." and the latest
    dataset through "output/analysis/latest.json",
  - output/analysis/: the five persisted analysis products
    (summary, timeseries, yearly and events CSVs plus
    latest.json) with a reduced column subset -- schema
    fidelity is protected by the analysis component tests
    (issues #21-#27),
  - output/plots/: minimal constructed PNGs (valid
    IHDR/IDAT/IEND with correct CRCs) in the product layout of
    the issue #32 plot set; real rendering is covered there.

* Acceptance criterion "no docs/output/ dependency": the
  controlled docs/ tree deliberately contains no copy of the
  scientific output; the tests assert that the referenced
  resources resolve exclusively through build/output/, which
  is copied from the real OUTPUT_DIR -- no manually
  maintained second copy (test-levels.md, section 4.5).

* build_pages binds its production paths as definition-time
  module constants (DOCS_DIR, OUTPUT_DIR, BUILD_DIR -- same
  non-injectable design family as F-010/F-013/F-015/F-018);
  the fixture redirects them with monkeypatch.setattr on the
  module (see tests/Findings.md, F-021).

* The CLI options of build_pages have no effect and the parsed
  arguments are discarded (see tests/Findings.md, F-020);
  a call without arguments would parse the *pytest* command
  line, so every test passes an explicit empty argv.

* Failure propagation is pinned: a missing docs/ directory
  fails the build with FileNotFoundError, while a missing
  output/ directory is currently tolerated with a warning
  only (see tests/Findings.md, F-021).

All tests are deterministic and require no network access.
"""

from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

import pytest

import src.update.build_pages as build_pages_module

# ------------------------------------------------------------------
# Controlled docs/ input (modeled on the production website)
# ------------------------------------------------------------------

_INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Test Build Page</title>
<link rel="stylesheet" href="css/style.css">
</head>
<body>
<header>
<h1>Test Build Page</h1>
<nav>
<a href="index.html">Home</a>
<a href="overview/results.html">Results</a>
</nav>
</header>
<main>
<figure class="plot">
<img class="plot-image"
     src="output/plots/sea_ice_geotiff_overview.png"
     alt="Overview">
</figure>
<figure class="plot">
<img class="plot-image"
     src="output/plots/timeseries/Test_Region_Water_relative.png"
     alt="Time Series">
</figure>
</main>
<footer>
<a
href="https://github.com/Chris010980/hudson_bay_sea_ice_showcase"
target="_blank"
>GitHub</a>
</footer>
<script>
fetch("output/analysis/latest.json")
</script>
</body>
</html>
"""

_RESULTS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Test Results Page</title>
<link rel="stylesheet" href="../css/style.css">
</head>
<body>
<header>
<h1>Results</h1>
<nav>
<a href="../index.html">Home</a>
</nav>
</header>
<main>
<figure class="plot">
<img class="plot-image"
     src="../output/plots/timeseries/Test_Region_Water_absolute.png"
     alt="Absolute">
</figure>
</main>
</body>
</html>
"""

_STYLE_CSS = (
    "body { font-family: sans-serif; }\n"
    ".plot-image { max-width: 100%; }\n"
)


# ------------------------------------------------------------------
# Controlled output/analysis/ input (reduced column subset)
# ------------------------------------------------------------------

# Hand calculations: Test Region Water covers 2500 km2 of water,
# so 60 % relative coverage is 60 * 2500 / 100 = 1500 km2 and
# 30 % absolute coverage is 30 * 2500 / 100 = 750 km2 (same
# synthetic region as the rest of the suite).
_SUMMARY_CSV = (
    "date,region,relative_coverage_percent,"
    "absolute_coverage_percent,relative_ice_area_km2,"
    "absolute_ice_area_km2\n"
    "2026-03-02,Test Region Water,60.0,30.0,1500.0,750.0\n"
)

_TIMESERIES_CSV = (
    "date,region,relative_coverage_percent,"
    "absolute_coverage_percent\n"
    "2026-01-15,Test Region Water,90.0,45.0\n"
    "2026-07-15,Test Region Water,20.0,10.0\n"
)

_YEARLY_CSV = (
    "region,year,relative_mean_coverage_percent,"
    "absolute_mean_coverage_percent\n"
    "Test Region Water,2000,50.0,25.0\n"
    "Test Region Water,2001,40.0,20.0\n"
)

_EVENTS_CSV = (
    "region,event_type,event_year,threshold_percent,"
    "event_date\n"
    "Test Region Water,break-up,2000,50.0,2000-07-01\n"
    "Test Region Water,freeze-up,2000,50.0,2000-11-10\n"
)

_LATEST_JSON = {
    "dataset": "synthetic-test-dataset",
    "date": "2026-03-02",
    "generated": "2026-03-02T12:00:00",
    "observations": 1234,
}

# The analysis products expected at the deployment path
# build/output/analysis/.
_ANALYSIS_PRODUCTS = [
    "ice_coverage_summary.csv",
    "ice_coverage_timeseries.csv",
    "ice_coverage_yearly.csv",
    "ice_coverage_events.csv",
    "latest.json",
]


# ------------------------------------------------------------------
# Controlled output/plots/ input (issue #32 product layout)
# ------------------------------------------------------------------

_PLOT_PRODUCTS = [
    "sea_ice_geotiff_overview.png",
    "sea_ice_geotiff_overview_regions.png",
    "timeseries/Test_Region_Water_relative.png",
    "timeseries/Test_Region_Water_absolute.png",
    "timeseries/anomalies/Test_Region_Water_relative_anomaly.png",
    "timeseries/thresholds/Test_Region_Water_threshold_duration.png",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _png_bytes() -> bytes:
    """Construct a deterministic valid 1 x 1 RGB PNG.

    The chunks are assembled with correct lengths and CRC
    checksums, so the result is a structurally valid PNG without
    depending on matplotlib: the build stage only copies files,
    and real plot rendering is covered by the issue #32 tests.
    """

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data

        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR: width 1, height 1, 8 bit depth, color type 2 (RGB).
    header = chunk(
        b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    )

    # One scanline: filter byte 0 followed by a single RGB pixel.
    pixel = chunk(b"IDAT", zlib.compress(b"\x00\x40\x80\xc0"))

    trailer = chunk(b"IEND", b"")

    return signature + header + pixel + trailer


def _seed_docs(docs_dir: Path) -> None:
    """Write the controlled static website (docs/ input)."""
    (docs_dir / "css").mkdir(parents=True)
    (docs_dir / "overview").mkdir()

    (docs_dir / "index.html").write_text(
        _INDEX_HTML,
        encoding="utf-8",
    )
    (docs_dir / "css" / "style.css").write_text(
        _STYLE_CSS,
        encoding="utf-8",
    )
    (docs_dir / "overview" / "results.html").write_text(
        _RESULTS_HTML,
        encoding="utf-8",
    )


def _seed_analysis(analysis_dir: Path) -> None:
    """Write the controlled analysis products (output/analysis/)."""
    analysis_dir.mkdir(parents=True)

    products = {
        "ice_coverage_summary.csv": _SUMMARY_CSV,
        "ice_coverage_timeseries.csv": _TIMESERIES_CSV,
        "ice_coverage_yearly.csv": _YEARLY_CSV,
        "ice_coverage_events.csv": _EVENTS_CSV,
    }

    for name, content in products.items():
        (analysis_dir / name).write_text(content, encoding="utf-8")

    (analysis_dir / "latest.json").write_text(
        json.dumps(_LATEST_JSON, indent=4) + "\n",
        encoding="utf-8",
    )


def _seed_plots(plots_dir: Path) -> None:
    """Write the controlled plot products (output/plots/)."""
    content = _png_bytes()

    for name in _PLOT_PRODUCTS:
        path = plots_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _file_inventory(root: Path, prefix: str = "") -> dict[str, bytes]:
    """Map every regular file below root to its relative path.

    The keys are POSIX-style relative paths (optionally below a
    prefix such as "output/"), the values the file contents, so
    two inventories can be compared for byte equality.
    """
    return {
        prefix + path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


_REFERENCE_PATTERN = re.compile(r'(?:href|src)="([^"]+)"')

_FETCH_PATTERN = re.compile(r'fetch\("([^"]+)"\)')


def _referenced_paths(page: Path) -> list[str]:
    """Extract the local resource paths referenced by a page.

    External links (http/https) and fragment anchors are
    filtered out; the remaining references are relative to the
    directory containing the page.
    """
    text = page.read_text(encoding="utf-8")

    candidates = _REFERENCE_PATTERN.findall(
        text
    ) + _FETCH_PATTERN.findall(text)

    return [
        reference
        for reference in candidates
        if not reference.startswith(("http://", "https://", "#"))
    ]


# ------------------------------------------------------------------
# Fixture: isolated build environment
# ------------------------------------------------------------------


@pytest.fixture
def build_pages_environment(
    test_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Path]:
    """Isolate the build stage (docs/ + output/ -> build/).

    Provides the controlled docs/ and output/ trees and
    redirects the definition-time module constants of
    build_pages (see tests/Findings.md, F-021) to the isolated
    directories, so no production path is touched.
    """
    root = test_environment["root"]
    docs_dir = root / "docs"
    output_dir = test_environment["output"]
    build_dir = test_environment["build"]

    _seed_docs(docs_dir)
    _seed_analysis(output_dir / "analysis")
    _seed_plots(output_dir / "plots")

    monkeypatch.setattr(build_pages_module, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(build_pages_module, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(build_pages_module, "BUILD_DIR", build_dir)

    return {
        "docs_dir": docs_dir,
        "output_dir": output_dir,
        "build_dir": build_dir,
    }


# ------------------------------------------------------------------
# Task: execute the build and validate the directory structure
# ------------------------------------------------------------------


def test_build_creates_expected_directory_structure(
    build_pages_environment: dict[str, Path],
) -> None:
    """The build assembles docs/ and output/ into build/.

    build/ contains the static website at its root and the
    complete generated output below build/output/; the file
    inventory is exactly the union of both controlled inputs
    with byte-identical copies (test-levels.md, section 4.5).
    """
    env = build_pages_environment

    built_dir = build_pages_module.main([])

    assert built_dir == env["build_dir"]

    expected = _file_inventory(env["docs_dir"]) | {
        "output/" + name: content
        for name, content in _file_inventory(env["output_dir"]).items()
    }

    assert _file_inventory(env["build_dir"]) == expected


# ------------------------------------------------------------------
# Task: validate the expected website files
# ------------------------------------------------------------------


def test_website_files_are_deployed_and_references_resolve(
    build_pages_environment: dict[str, Path],
) -> None:
    """The expected website files exist and references resolve.

    Every local resource referenced by the built pages
    (stylesheets, nested pages, plot figures, latest.json)
    resolves below build/. The scientific resources resolve
    exclusively through build/output/ -- the controlled docs/
    tree deliberately contains no copy of output/, so the build
    introduces no manually maintained docs/output/ dependency.
    """
    env = build_pages_environment
    build_dir = env["build_dir"]

    build_pages_module.main([])

    for name in (
        "index.html",
        "css/style.css",
        "overview/results.html",
    ):
        path = build_dir / name

        assert path.is_file()
        assert path.stat().st_size > 0

    for page in (
        build_dir / "index.html",
        build_dir / "overview" / "results.html",
    ):
        for reference in _referenced_paths(page):
            assert (page.parent / reference).resolve().is_file(), (
                reference
            )

    # No scientific output was required inside docs/.
    assert not (env["docs_dir"] / "output").exists()


# ------------------------------------------------------------------
# Task: validate the expected scientific output paths
# ------------------------------------------------------------------


def test_scientific_output_is_available_at_deployment_paths(
    build_pages_environment: dict[str, Path],
) -> None:
    """output/analysis/ and output/plots/ are deployed below build/.

    The analysis products and plot products referenced by the
    website exist at their deployment paths; latest.json carries
    the controlled payload and the plot copies are the
    byte-identical valid PNGs of the controlled input.
    """
    env = build_pages_environment
    build_dir = env["build_dir"]

    build_pages_module.main([])

    analysis_dir = build_dir / "output" / "analysis"

    for name in _ANALYSIS_PRODUCTS:
        path = analysis_dir / name

        assert path.is_file()
        assert path.stat().st_size > 0

    deployed_latest = json.loads(
        (analysis_dir / "latest.json").read_text(encoding="utf-8")
    )

    assert deployed_latest == _LATEST_JSON

    plots_dir = build_dir / "output" / "plots"
    expected_png = _png_bytes()

    for name in _PLOT_PRODUCTS:
        content = (plots_dir / name).read_bytes()

        assert content.startswith(b"\x89PNG\r\n\x1a\n")
        assert content == expected_png


# ------------------------------------------------------------------
# Task: validate reproducible build results
# ------------------------------------------------------------------


def test_rebuild_is_reproducible_and_removes_stale_files(
    build_pages_environment: dict[str, Path],
) -> None:
    """A rebuild produces byte-identical results and drops stale files.

    build/ always starts from scratch: products of a previous
    build (here: a stale plot of an older layout and an orphan
    file at the build root) are removed, and two consecutive
    builds yield identical file inventories (acceptance
    criterion: reproducible build results).
    """
    env = build_pages_environment
    build_dir = env["build_dir"]

    stale_plot = build_dir / "output" / "old_product.png"
    stale_plot.parent.mkdir(parents=True, exist_ok=True)
    stale_plot.write_bytes(b"stale")

    (build_dir / "orphan.txt").write_bytes(b"stale")

    build_pages_module.main([])

    assert not stale_plot.exists()
    assert not (build_dir / "orphan.txt").exists()

    first_inventory = _file_inventory(build_dir)

    build_pages_module.main([])

    second_inventory = _file_inventory(build_dir)

    assert first_inventory == second_inventory


# ------------------------------------------------------------------
# Failure propagation
# ------------------------------------------------------------------


def test_missing_docs_directory_fails_the_build(
    build_pages_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing docs/ directory propagates FileNotFoundError.

    The static website is the one mandatory build input; the
    build must not silently produce a scientific-only or empty
    site.
    """
    env = build_pages_environment

    monkeypatch.setattr(
        build_pages_module,
        "DOCS_DIR",
        env["docs_dir"].parent / "missing_docs",
    )

    with pytest.raises(FileNotFoundError):
        build_pages_module.main([])


def test_missing_output_directory_is_tolerated(
    build_pages_environment: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinned current behavior: a missing output/ only warns.

    The build succeeds and deploys the static website, but no
    scientific product is copied and build/output/ is absent
    (see tests/Findings.md, F-021). The tests pin the
    implemented tolerance instead of assuming a fail-fast
    behavior that the code does not implement.
    """
    env = build_pages_environment

    monkeypatch.setattr(
        build_pages_module,
        "OUTPUT_DIR",
        env["output_dir"].parent / "missing_output",
    )

    build_pages_module.main([])

    assert (env["build_dir"] / "index.html").is_file()
    assert not (env["build_dir"] / "output").exists()

    assert _file_inventory(env["build_dir"]) == _file_inventory(
        env["docs_dir"]
    )
