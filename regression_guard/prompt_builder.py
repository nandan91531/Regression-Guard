from regression_guard.sanitizer import sanitize_failure_output

def build_test_generation_prompt(diff_text: str, failure_output: str) -> str:
    """
    Constructs a generic test-generation prompt without domain-specific prompt leakage.
    """
    sanitized_failure = sanitize_failure_output(failure_output)
    prompt = f"""You are an expert Python developer writing a pytest regression test function for a bug fix.

Here is the source code diff that fixed the bug:
```diff
{diff_text}
```

Here is the pytest failure output showing the bug before the fix:
```
{sanitized_failure}
```

TASK: Write EXACTLY ONE pytest test function with ONLY ONE assert statement testing the boundary condition modified in the diff above.

EXAMPLE OUTPUT FORMAT (Use your target module and function, not these placeholder names):
```python
import target_module

def test_feature_boundary():
    assert target_module.target_function(input_value) == expected_output
```

CRITICAL INSTRUCTIONS:
1. In the failure log above, expected outputs were masked as `[HIDDEN - infer this from the fix logic]`. Do NOT write `[HIDDEN]` in your Python code!
2. READ THE DIFF COMMENTS CAREFULLY: Look for example input numbers mentioned in the diff comments (e.g. `999999`). Use THAT EXACT boundary input number!
3. ASSERT THE NEW FIXED OUTPUT: The diff comments state what the old buggy code outputted (e.g. `1000.0 kB`) vs what the new fixed code reads (e.g. `1.0 MB`). You MUST assert the new FIXED output string (`'1.0 MB'`) as your expected_output, NOT the old buggy string!
4. Always use top-level package imports (e.g. `import package_name`). Call `<package_name>.<function_name>(...)`.
5. Write ONLY ONE assertion in ONE test function. DO NOT add multiple assertions or extra test cases!
6. Output ONLY the ```python ... ``` code block. Do NOT include markdown explanations outside the code block.
"""
    return prompt

def build_retry_prompt(diff_text: str, failure_output: str, previous_test: str, why_it_failed: str) -> str:
    """
    Constructs a generic retry prompt when a generated test fails validation.
    """
    sanitized_failure = sanitize_failure_output(failure_output)
    prompt = f"""You are an expert Python developer writing a single pytest regression test function.

Here is the source code diff that fixed the bug:
```diff
{diff_text}
```

Here is the original test failure output:
```
{sanitized_failure}
```

Your PREVIOUS test code attempt was:
```python
{previous_test}
```

That attempt FAILED validation because:
{why_it_failed}

TASK: Write EXACTLY ONE corrected test function with ONLY ONE assert statement.

EXAMPLE OUTPUT FORMAT (Use your target module and function, not these placeholder names):
```python
import target_module

def test_feature_boundary():
    assert target_module.target_function(input_value) == expected_output
```

CRITICAL INSTRUCTIONS FOR CORRECTION:
1. In failure logs, expected outputs are masked as `[HIDDEN - infer this from the fix logic]`. Do NOT write `[HIDDEN]` in your code!
2. INPUT VALUE: Use the exact boundary input number mentioned in the diff comments (e.g. `999999`). Do NOT use round numbers like `1000000` or `1024` that do not trigger the boundary bug!
3. ASSERTION TARGET: If your previous test asserted the old buggy result (e.g. `'1000.0 kB'`), CHANGE IT to assert the NEW FIXED output string (`'1.0 MB'`) produced by the fixed code!
4. Always use top-level package imports (e.g. `import package_name`).
5. Write EXACTLY ONE test function with ONLY ONE assertion.
6. Output ONLY the ```python ... ``` code block. Do NOT include explanations outside the code block.
"""
    return prompt

def build_root_cause_prompt(diff_text: str) -> str:
    """
    Asks Ollama to explain WHY the bug happened in plain language for inclusion in the report.
    """
    prompt = f"""Here is a code diff that fixed a bug:

{diff_text}

In 2-3 simple sentences, explain what the bug was and why it happened.
Do not include code, just a plain-language explanation.
"""
    return prompt
