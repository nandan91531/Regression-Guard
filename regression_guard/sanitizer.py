import re

def clean_failure_output(output: str) -> str:
    """
    Extracts key failure markers and tracebacks from raw pytest output to keep prompts concise.
    """
    if not output:
        return "No test failure output recorded."
    lines = output.strip().splitlines()
    relevant = []
    for line in lines:
        if any(k in line for k in ["FAILED", "AssertionError", "E   ", ">   ", "short test summary", "assert "]):
            relevant.append(line)
    if len(relevant) > 0:
        return "\n".join(relevant[-40:])
    return "\n".join(lines[-40:])

def sanitize_failure_output(output: str) -> str:
    """
    Masks human-written expected output values in pytest logs to prevent prompt answer leakage.
    
    Replaces expected values in equality assertions, diff markers, and parametrized test markers
    with '[HIDDEN - infer this from the fix logic]'.
    """
    cleaned = clean_failure_output(output)
    if not cleaned:
        return "No test failure output recorded."
    lines = cleaned.strip().splitlines()
    sanitized = []
    for line in lines:
        if "assert" in line and "==" in line:
            line = re.sub(r"(assert\s+.*?==\s*).*$", r"\1[HIDDEN - infer this from the fix logic]", line)
        if re.search(r"(\b-\s+|\bE\s+-\s+)", line):
            line = re.sub(r"(\b-\s+|\bE\s+-\s+).*$", r"\1[HIDDEN - infer this from the fix logic]", line)
        line = re.sub(r"\[(test_args\d+)-[^\]]+\]", r"[\1]", line)
        sanitized.append(line)
    return "\n".join(sanitized)

def extract_python_code(test_code: str) -> str:
    """
    Extracts pure Python code from LLM responses containing markdown code blocks.
    Handles ```python, ```py, and raw code snippets.
    """
    match = re.search(r"```(?:python|py)?\s*(.*?)\s*```", test_code, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return test_code.strip()

def save_generated_test(test_code: str, filepath: str) -> str:
    """
    Extracts Python code and saves it to disk.
    """
    cleaned_code = extract_python_code(test_code)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(cleaned_code)
    print(f"Saved generated test to {filepath}")
    return cleaned_code
