import os
import subprocess
from typing import Optional

def ensure_version_files(workspace_path: str, src_subfolder: Optional[str] = "src") -> list[str]:
    """
    Dynamically discovers Python packages inside workspace_path / src_subfolder
    and ensures a stand-in _version.py file exists to satisfy setuptools-scm
    or dynamic versioning dependencies when running directly from source.
    """
    search_dir = os.path.join(workspace_path, src_subfolder) if src_subfolder else workspace_path
    if not os.path.exists(search_dir):
        return []

    created_files = []
    # Find top-level Python package subdirectories
    for item in os.listdir(search_dir):
        item_path = os.path.join(search_dir, item)
        if os.path.isdir(item_path) and not item.startswith((".", "_")) and item != "tests":
            version_file = os.path.join(item_path, "_version.py")
            if not os.path.exists(version_file):
                try:
                    with open(version_file, "w", encoding="utf-8") as f:
                        f.write('__version__ = "0.0.0"\n')
                    created_files.append(version_file)
                    print(f"Created stand-in version file at {version_file}")
                except Exception as e:
                    print(f"Warning: Could not write version file at {version_file}: {e}")

    return created_files

def run_tests(
    workspace_path: str,
    test_path: Optional[str] = None,
    src_subfolder: Optional[str] = "src"
) -> subprocess.CompletedProcess:
    """
    Runs pytest inside the specified workspace directory with custom PYTHONPATH.
    """
    cmd = ["pytest"]
    if test_path:
        cmd.append(test_path)

    env = os.environ.copy()
    if src_subfolder:
        src_full_path = os.path.abspath(os.path.join(workspace_path, src_subfolder))
        env["PYTHONPATH"] = src_full_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        cwd=workspace_path,
        capture_output=True,
        text=True,
        check=False,
        env=env
    )
    return result
