"""Google Colab bootstrap for worldmaker.

Colab starts with a bare working directory, so `import worldmaker` fails until
the repository is on disk and on `sys.path`. Drop this at the top of a Colab
notebook:

    !wget -q https://raw.githubusercontent.com/pmcray/worldmaker/master/colab_setup.py
    import colab_setup; colab_setup.setup()

or, in one cell without downloading this file first:

    !git clone -q https://github.com/pmcray/worldmaker.git
    %cd worldmaker
    import colab_setup; colab_setup.setup()

`setup()` is safe to run repeatedly and works outside Colab too, where it
simply puts the checkout on `sys.path`.
"""
import importlib
import os
import subprocess
import sys

REPO_URL = "https://github.com/pmcray/worldmaker.git"
REPO_DIR = "worldmaker"
PACKAGE = "worldmaker"

# Colab already ships numpy, pandas, matplotlib, networkx, plotly, PIL and
# ipywidgets. Only OpenCV is sometimes absent, and only the planet texture
# pipeline needs it.
_OPTIONAL = {
    "cv2": "opencv-python-headless",
    "PIL": "pillow",
    "plotly": "plotly",
    "matplotlib": "matplotlib",
    "networkx": "networkx",
    "ipywidgets": "ipywidgets",
    "pandas": "pandas",
    "numpy": "numpy",
}


def in_colab() -> bool:
    """True when running inside Google Colab."""
    return "google.colab" in sys.modules or os.path.isdir("/content")


def _run(cmd) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ! {' '.join(cmd)}\n    {result.stderr.strip()[:300]}")
    return result.returncode == 0


def _find_package_root(start: str = ".") -> str:
    """Locates the directory containing the `worldmaker` package."""
    candidates = [
        start,
        os.path.join(start, REPO_DIR),
        "/content/" + REPO_DIR,
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, PACKAGE, "__init__.py")):
            return os.path.abspath(candidate)
    return ""


def clone_repository(branch: str = None, force: bool = False) -> str:
    """Clones the repository if it is not already present."""
    root = _find_package_root()
    if root and not force:
        return root

    target = "/content" if os.path.isdir("/content") else "."
    dest = os.path.join(target, REPO_DIR)

    if os.path.isdir(dest) and force:
        subprocess.run(["rm", "-rf", dest], check=False)

    if not os.path.isdir(dest):
        print(f"Cloning {REPO_URL} ...")
        cmd = ["git", "clone", "--quiet", REPO_URL, dest]
        if branch:
            cmd = ["git", "clone", "--quiet", "--branch", branch, REPO_URL, dest]
        if not _run(cmd):
            raise RuntimeError(
                "Could not clone the repository. If it is private, clone it "
                "manually with your credentials and re-run setup()."
            )
    return os.path.abspath(dest)


def install_dependencies(extras: bool = True, quiet: bool = True) -> None:
    """Installs whatever Colab does not already provide."""
    missing = []
    for module, package in _OPTIONAL.items():
        if module in ("cv2", "plotly", "matplotlib", "networkx",
                      "ipywidgets") and not extras:
            continue
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)

    if not missing:
        print("Dependencies: all present")
        return

    print(f"Installing: {', '.join(missing)}")
    cmd = [sys.executable, "-m", "pip", "install"]
    if quiet:
        cmd.append("--quiet")
    cmd += missing
    _run(cmd)


def setup(branch: str = None, extras: bool = True, install: bool = True,
          verbose: bool = True):
    """Prepares the environment and imports the package.

    Clones the repository if needed, puts it on `sys.path`, installs any
    missing dependencies, and returns the imported `worldmaker` module.
    """
    root = _find_package_root()
    if not root:
        root = clone_repository(branch=branch)

    if root not in sys.path:
        sys.path.insert(0, root)

    # Run from the checkout, so relative output paths land beside the code
    if os.path.isdir(root) and os.getcwd() != root:
        os.chdir(root)

    if install:
        install_dependencies(extras=extras)

    # Drop any partially imported copy, so a re-run picks up a fresh checkout
    for name in [m for m in sys.modules if m == PACKAGE
                 or m.startswith(PACKAGE + ".")]:
        del sys.modules[name]

    module = importlib.import_module(PACKAGE)

    if verbose:
        print(f"worldmaker ready from {root}")
        print(f"  python {sys.version.split()[0]}"
              f"{' | Google Colab' if in_colab() else ''}")
        try:
            import worldmaker.planet as _planet  # noqa: F401
            print("  planet rendering: available")
        except ImportError:
            pass
    return module


if __name__ == "__main__":
    setup()
