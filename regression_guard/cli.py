import os
import shutil
import sys
from typing import Callable, Optional

from regression_guard.config import Config, parse_args
from regression_guard.git_utils import (
    clone_repo,
    checkout_commit,
    copy_file,
    get_diff,
    get_source_only_diff,
    remove_readonly
)
from regression_guard.test_runner import ensure_version_files, run_tests
from regression_guard.sanitizer import (
    clean_failure_output,
    extract_python_code,
    save_generated_test
)
from regression_guard.llm_client import LLMClient, LLMClientError
from regression_guard.prompt_builder import (
    build_test_generation_prompt,
    build_retry_prompt,
    build_root_cause_prompt
)
from regression_guard.reporter import generate_report

def cleanup_workspaces(config: Config, log: Callable[[str], None] = print) -> None:
    """Removes temporary workspace directories unless --keep-workspaces is specified."""
    if not config.keep_workspaces:
        for ws in [config.buggy_workspace, config.fixed_workspace]:
            if os.path.exists(ws):
                try:
                    shutil.rmtree(ws, onexc=remove_readonly)
                    log(f"Cleaned up workspace {ws}")
                except Exception as e:
                    log(f"Warning: Could not remove {ws}: {e}")

def run(config: Config, log_callback: Optional[Callable[[str], None]] = None) -> int:
    """
    Executes the full Regression Guard workflow based on the provided configuration.
    """
    def log(msg: str):
        print(msg)
        if log_callback:
            log_callback(msg)

    log(f"🚀 Starting Regression Guard for {config.repo}...")
    log(f"Buggy commit: {config.buggy_commit} | Fixed commit: {config.fixed_commit}")

    try:
        # Step 1: Workspace Setup
        log("STEP_1: Workspace Setup")
        clone_repo(config.repo, config.buggy_workspace)
        checkout_commit(config.buggy_workspace, config.buggy_commit)
        ensure_version_files(config.buggy_workspace, config.src_subfolder)

        clone_repo(config.repo, config.fixed_workspace)
        checkout_commit(config.fixed_workspace, config.fixed_commit)
        ensure_version_files(config.fixed_workspace, config.src_subfolder)

        # Copy human-written fixed test file into buggy workspace for initial bug confirmation
        source_test_path = os.path.join(config.fixed_workspace, config.test_file)
        dest_test_dir = os.path.join(config.buggy_workspace, os.path.dirname(config.test_file))
        copy_file(source_test_path, dest_test_dir)

        # Step 2: Extract Diffs
        log("STEP_2: Extract Diffs")
        diff_text = get_diff(config.repo, config.buggy_commit, config.fixed_commit)
        source_diff = get_source_only_diff(
            config.repo, config.buggy_commit, config.fixed_commit, config.test_file
        )

        log("=== FULL DIFF ===")
        log(diff_text)

        # Step 3: Run Bug Confirmation Step
        log("STEP_3: Bug Confirmation")
        buggy_result = run_tests(config.buggy_workspace, config.test_file, src_subfolder=config.src_subfolder)
        fixed_result = run_tests(config.fixed_workspace, config.test_file, src_subfolder=config.src_subfolder)

        log(f"Buggy exit code: {buggy_result.returncode}")
        log(f"Fixed exit code: {fixed_result.returncode}")

        if buggy_result.returncode != 0 and fixed_result.returncode == 0:
            log("\n✅ Bug CONFIRMED: fails on buggy version, passes on fixed version.")
        else:
            log("\n❌ Could not confirm bug pattern (check exit codes above).")

        # Step 4: AI Test Generation + Validation Loop
        log("STEP_4: AI Generation & Validation")
        llm = LLMClient(model=config.model, ollama_url=config.ollama_url, timeout=config.timeout)
        valid_test = None
        prompt = build_test_generation_prompt(source_diff, buggy_result.stdout)

        for attempt in range(1, config.max_attempts + 1):
            log(f"\n--- Attempt {attempt}/{config.max_attempts} ---")
            try:
                generated_raw = llm.generate(prompt)
            except LLMClientError as e:
                log(f"❌ LLM Generation error: {e}")
                return 1

            generated_test = extract_python_code(generated_raw)
            log(generated_test)

            buggy_gen_file = os.path.join(config.buggy_workspace, "test_generated.py")
            fixed_gen_file = os.path.join(config.fixed_workspace, "test_generated.py")
            save_generated_test(generated_test, buggy_gen_file)
            save_generated_test(generated_test, fixed_gen_file)

            buggy_gen_result = run_tests(config.buggy_workspace, "test_generated.py", src_subfolder=config.src_subfolder)
            fixed_gen_result = run_tests(config.fixed_workspace, "test_generated.py", src_subfolder=config.src_subfolder)

            log(f"Buggy exit code: {buggy_gen_result.returncode}")
            log(f"Fixed exit code: {fixed_gen_result.returncode}")

            if buggy_gen_result.returncode != 0 and fixed_gen_result.returncode == 0:
                log("✅ Valid test found!")
                valid_test = generated_test
                break
            else:
                log("❌ Invalid test, retrying with feedback...")
                reasons = []
                if buggy_gen_result.returncode == 0 and fixed_gen_result.returncode == 0:
                    reasons.append("The test PASSED on BOTH buggy and fixed code. Choose a boundary input value specifically affected by the fix diff.")
                elif buggy_gen_result.returncode != 0 and fixed_gen_result.returncode != 0:
                    buggy_err = clean_failure_output(buggy_gen_result.stdout or buggy_gen_result.stderr)
                    fixed_err = clean_failure_output(fixed_gen_result.stdout or fixed_gen_result.stderr)
                    reasons.append(f"The test FAILED on BOTH versions.\nBuggy failure:\n{buggy_err}\nFixed failure:\n{fixed_err}")
                elif buggy_gen_result.returncode == 0 and fixed_gen_result.returncode != 0:
                    fixed_err = clean_failure_output(fixed_gen_result.stdout or fixed_gen_result.stderr)
                    reasons.append(f"The test PASSED on buggy code but FAILED on fixed code.\nFixed execution output:\n{fixed_err}\nDIAGNOSIS: You asserted the old buggy behavior instead of the correct fixed output.")

                why_it_failed = "\n".join(reasons)
                prompt = build_retry_prompt(source_diff, buggy_result.stdout, generated_test, why_it_failed)

        # Step 5: Report Generation
        if valid_test:
            log("STEP_5: Generating Final Report")
            log(f"\n🎉 FINAL VALID TEST:\n{valid_test}")
            try:
                root_cause_prompt = build_root_cause_prompt(diff_text)
                root_cause_explanation = llm.generate(root_cause_prompt)
            except LLMClientError as e:
                root_cause_explanation = f"Could not generate root cause explanation: {e}"

            log("\n--- ROOT CAUSE EXPLANATION ---")
            log(root_cause_explanation)

            generate_report(
                diff_text=diff_text,
                root_cause=root_cause_explanation,
                final_test=valid_test,
                buggy_output=buggy_gen_result.stdout,
                fixed_output=fixed_gen_result.stdout,
                output_filepath=config.output_report
            )
            log("STEP_COMPLETE")
            return 0
        else:
            log(f"\n⚠️ Could not generate a valid test after {config.max_attempts} attempts.")
            return 1
    finally:
        cleanup_workspaces(config, log=log)

def main(args: Optional[list[str]] = None) -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    config = parse_args(args)
    sys.exit(run(config))

if __name__ == "__main__":
    main()
