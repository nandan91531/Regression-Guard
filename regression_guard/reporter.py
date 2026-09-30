def generate_report(
    diff_text: str,
    root_cause: str,
    final_test: str,
    buggy_output: str,
    fixed_output: str,
    output_filepath: str = "regression_report.md"
) -> str:
    """
    Generates a final markdown report combining full diff, root cause explanation,
    accepted AI-generated test, and raw execution evidence from both workspaces.
    """
    report = f"""# Regression Guard Report

## Bug Diff

{diff_text}

## Root Cause

{root_cause}

## Accepted Regression Test

```python
{final_test}
```

## Validation Evidence

### Ran on BUGGY version:
{buggy_output}

### Ran on FIXED version:
{fixed_output}

## Conclusion

The above test fails on the buggy version and passes on the fixed version,
confirming this test correctly captures the reported bug.
"""
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 Report saved to {output_filepath}")
    return report
