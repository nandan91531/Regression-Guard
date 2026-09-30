import argparse
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    repo: str = "humanize"
    buggy_commit: str = "7574e0c"
    fixed_commit: str = "823ad60"
    test_file: str = "tests/test_filesize.py"
    src_subfolder: str = "src"
    model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"
    timeout: int = 180
    max_attempts: int = 3
    output_report: str = "regression_report.md"
    buggy_workspace: str = "buggy_workspace"
    fixed_workspace: str = "fixed_workspace"
    keep_workspaces: bool = False

def parse_args(args: Optional[list[str]] = None) -> Config:
    parser = argparse.ArgumentParser(
        description="Regression Guard: Automated LLM-driven boundary regression test generator & bug reporter."
    )
    parser.add_argument("--repo", type=str, default="humanize", help="Path or URL of the target Git repository")
    parser.add_argument("--buggy", type=str, default="7574e0c", help="Commit hash for the buggy state")
    parser.add_argument("--fixed", type=str, default="823ad60", help="Commit hash for the fixed state")
    parser.add_argument("--test-file", type=str, default="tests/test_filesize.py", help="Target test file path within repo")
    parser.add_argument("--src-subfolder", type=str, default="src", help="Source subfolder relative to workspace root (e.g. 'src' or '')")
    parser.add_argument("--model", type=str, default="llama3.2", help="Ollama LLM model name")
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Base URL of local Ollama API server")
    parser.add_argument("--timeout", type=int, default=180, help="Ollama API HTTP request timeout in seconds")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum test generation retry attempts")
    parser.add_argument("--output-report", type=str, default="regression_report.md", help="Path to write the markdown report")
    parser.add_argument("--buggy-workspace", type=str, default="buggy_workspace", help="Directory for buggy workspace")
    parser.add_argument("--fixed-workspace", type=str, default="fixed_workspace", help="Directory for fixed workspace")
    parser.add_argument("--keep-workspaces", action="store_true", help="Keep temporary buggy and fixed workspace directories after completion")

    parsed = parser.parse_args(args)
    return Config(
        repo=parsed.repo,
        buggy_commit=parsed.buggy,
        fixed_commit=parsed.fixed,
        test_file=parsed.test_file,
        src_subfolder=parsed.src_subfolder,
        model=parsed.model,
        ollama_url=parsed.ollama_url,
        timeout=parsed.timeout,
        max_attempts=parsed.max_attempts,
        output_report=parsed.output_report,
        buggy_workspace=parsed.buggy_workspace,
        fixed_workspace=parsed.fixed_workspace,
        keep_workspaces=parsed.keep_workspaces,
    )
