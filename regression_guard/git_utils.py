import os
import shutil
import stat
import subprocess
import time

def remove_readonly(func, path, excinfo):
    """
    Helper function to remove read-only attributes from files during directory cleanup.
    Required on Windows when deleting Git repository directories (.git objects).
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def safe_rmtree(path: str) -> None:
    """
    Safely removes a directory tree on Windows, falling back to directory renaming
    if another process holds transient file locks.
    """
    if not os.path.exists(path):
        return
    try:
        shutil.rmtree(path, onexc=remove_readonly)
    except Exception:
        try:
            temp_path = f"{path}_old_{int(time.time())}"
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
            os.rename(path, temp_path)
            shutil.rmtree(temp_path, ignore_errors=True)
        except Exception:
            pass

def clone_repo(repo_path: str, destination: str) -> None:
    """
    Clones a Git repository into a destination directory.
    If repo_path is a local path, uses local clone flags for speed optimization.
    Cleans up existing destination directories first.
    """
    safe_rmtree(destination)

    cmd = ["git", "clone"]
    if os.path.exists(repo_path):
        # Use shared local cloning for disk & speed optimization
        cmd.extend(["--shared", "--local"])
    cmd.extend([repo_path, destination])

    subprocess.run(cmd, check=True)
    print(f"Cloned into {destination}")

def checkout_commit(workspace_path: str, commit_hash: str) -> None:
    """
    Force checks out a specific Git commit hash within the workspace directory.
    """
    subprocess.run(["git", "checkout", "-f", commit_hash], cwd=workspace_path, check=True)
    print(f"Checked out {commit_hash} in {workspace_path}")

def copy_file(source_file: str, destination_folder: str) -> None:
    """
    Copies a file into destination_folder, creating directories if needed.
    """
    os.makedirs(destination_folder, exist_ok=True)
    shutil.copy(source_file, destination_folder)
    print(f"Copied {source_file} into {destination_folder}")

def get_diff(repo_path: str, buggy_hash: str, fixed_hash: str) -> str:
    """
    Runs 'git diff <buggy_hash> <fixed_hash>' inside the given repository.
    Produces full diff showing source code and test code changes.
    """
    result = subprocess.run(
        ["git", "diff", buggy_hash, fixed_hash],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout

def get_source_only_diff(repo_path: str, buggy_hash: str, fixed_hash: str, test_file_path: str) -> str:
    """
    Excludes test file changes from the diff passed to the LLM to prevent answer leakage.
    """
    cmd = ["git", "diff", buggy_hash, fixed_hash, "--", "."]
    if test_file_path:
        cmd.append(f":(exclude){test_file_path}")

    result = subprocess.run(
        cmd,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout
