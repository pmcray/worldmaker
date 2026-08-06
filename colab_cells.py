"""Makes the notebooks runnable on Google Colab.

Colab opens a notebook straight from GitHub into an empty runtime: no
clone, no `requirements.txt`, no `worldmaker` package on the path. Each
notebook therefore carries a bootstrap cell that installs the package from
GitHub when — and only when — it is running on Colab. Locally the same cell
does nothing and the clone's own copy of the package is used.

The inserted cells are tagged, so this script is idempotent: run it again
to refresh them in place rather than stacking duplicates.

    python colab_cells.py
"""
import json
import os
import sys

REPO = "pmcray/worldmaker"

# The branch, tag or commit Colab installs from. `master` still holds only
# the first two commits of the project: everything since — the package as
# it now stands, and the Sector Explorer itself — lives on this branch. Re-run
# this script with a ref argument once the work is merged:
#
#     python colab_cells.py master
DEFAULT_REF = "claude/status-colab-notebooks-w4tnm6"

BADGE_TAG = "colab-badge"
BOOTSTRAP_TAG = "colab-bootstrap"
DOWNLOAD_TAG = "colab-download"


def _cell(cell_type, tag, source):
    # The tag doubles as the cell id: stable across runs, and unique
    # because each of these cells appears at most once in a notebook.
    cell = {"cell_type": cell_type,
            "id": tag,
            "metadata": {"tags": [tag]},
            "source": source.strip("\n").splitlines(keepends=True)}
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


def badge_cell(filename, ref=DEFAULT_REF):
    """The Open in Colab badge GitHub renders at the top of a notebook."""
    url = f"https://colab.research.google.com/github/{REPO}/blob/{ref}/{filename}"
    return _cell("markdown", BADGE_TAG, f"""
<a href="{url}" target="_parent"><img
src="https://colab.research.google.com/assets/colab-badge.svg"
alt="Open In Colab"/></a>
""")


def bootstrap_cell(ref=DEFAULT_REF):
    """Installs the package on Colab; a no-op anywhere else."""
    return _cell("code", BOOTSTRAP_TAG, f'''
# --- Colab bootstrap -------------------------------------------------
# On Google Colab this fetches worldmaker from GitHub, so there is nothing
# to install by hand. Run from a clone of the repository it finds the local
# package instead and does nothing. Either way it is safe to re-run.
WORLDMAKER_REF = "{ref}"     # branch, tag or commit to fetch on Colab

import os
import subprocess
import sys

IN_COLAB = "google.colab" in sys.modules
REPO = "https://github.com/{REPO}.git"
CLONE = "/content/worldmaker"

if IN_COLAB:
    installed = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         f"git+{{REPO}}@{{WORLDMAKER_REF}}"]).returncode == 0

    if not installed:
        # A ref from before the package carried its packaging metadata:
        # clone it and import it where it stands.
        print(f"pip install of {{WORLDMAKER_REF}} failed; cloning instead")
        if not os.path.isdir(CLONE):
            subprocess.run(["git", "clone", "--depth", "1",
                            "--branch", WORLDMAKER_REF, REPO, CLONE],
                           check=True)
        sys.path.insert(0, CLONE)

    # Canon fetched from travellermap.com is cached beside the notebook
    # rather than inside site-packages.
    os.environ.setdefault("WORLDMAKER_CANON_CACHE", "/content/canon_cache")

try:
    import worldmaker as wm
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "worldmaker not found. Start Jupyter from the root of a clone of "
        "the repository, or install it with\\n"
        f"    pip install git+{{REPO}}") from None

print("worldmaker", getattr(wm, "__version__", "(unversioned)"),
      "ready" + (" on Colab" if IN_COLAB else ""))
''')


def download_cell(source):
    """A closing cell that hands the generated files back to the browser."""
    return _cell("code", DOWNLOAD_TAG, source)


EXPLORER_DOWNLOAD = """
# Colab keeps its files in a runtime that is thrown away when the session
# ends. This zips everything section 9 wrote and downloads it. Locally it
# just says where the files are.
import shutil
import sys

if "google.colab" in sys.modules:
    from google.colab import files
    archive = shutil.make_archive(str(out), "zip", out)
    print("downloading", archive)
    files.download(archive)
else:
    print("the sector is in", out.resolve())
"""

GENERATOR_DOWNLOAD = """
# On Colab, take the map and the sector data away with you before the
# runtime is recycled.
import sys
from pathlib import Path

written = ["sector_map.svg", "sector.sec"]

if "google.colab" in sys.modules:
    from google.colab import files
    for name in written:
        files.download(name)
else:
    for name in written:
        print(Path(name).resolve())
"""

BUILDER_DOWNLOAD = """
# Write the dossier and the surface map out, and on Colab — whose runtime
# is thrown away when the session ends — download them.
import sys
from pathlib import Path

out = Path("output")
out.mkdir(exist_ok=True)

dossier = out / f"{system.name.replace(' ', '_')}_dossier.md"
surface = out / f"{system.name.replace(' ', '_')}_mainworld_map.svg"
dossier.write_text(wm.export_system_markdown(system))
surface.write_text(wm.render_world_map_svg(mw, terrain))
print("written:", dossier, "and", surface)

if "google.colab" in sys.modules:
    from google.colab import files
    files.download(str(dossier))
    files.download(str(surface))
"""


def _find_tag(cells, tag):
    for index, cell in enumerate(cells):
        if tag in cell.get("metadata", {}).get("tags", []):
            return index
    return None


def ensure(path, download=None, ref=DEFAULT_REF):
    """Adds — or refreshes — the Colab cells in one notebook."""
    with open(path) as handle:
        notebook = json.load(handle)
    cells = notebook["cells"]

    badge = badge_cell(os.path.basename(path), ref)
    index = _find_tag(cells, BADGE_TAG)
    if index is None:
        cells.insert(0, badge)
    else:
        cells[index] = badge

    index = _find_tag(cells, BOOTSTRAP_TAG)
    if index is not None:
        cells.pop(index)
    # Under the notebook's own title, above its first section, and always
    # before any code has tried to import the package.
    position = 2 if len(cells) > 1 and cells[1]["cell_type"] == "markdown" else 1
    first_code = next(i for i, c in enumerate(cells) if c["cell_type"] == "code")
    cells.insert(min(position, first_code), bootstrap_cell(ref))

    if download is not None:
        cell = download_cell(download)
        index = _find_tag(cells, DOWNLOAD_TAG)
        if index is None:
            cells.append(cell)
        else:
            cells[index] = cell

    with open(path, "w") as handle:
        json.dump(notebook, handle, indent=1)
        handle.write("\n")

    return len(cells)


NOTEBOOKS = {
    "Traveller_Sector_Explorer.ipynb": EXPLORER_DOWNLOAD,
    "Traveller_System_Builder.ipynb": BUILDER_DOWNLOAD,
    "traveller_world_generator.ipynb": GENERATOR_DOWNLOAD,
}


def main(ref=DEFAULT_REF):
    for name, download in NOTEBOOKS.items():
        count = ensure(name, download=download, ref=ref)
        print(f"{name}: {count} cells, Colab cells in place (ref {ref})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REF)
