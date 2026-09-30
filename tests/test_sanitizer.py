from regression_guard.sanitizer import sanitize_failure_output, extract_python_code

def test_sanitize_failure_output_masks_expected_string():
    raw_output = "AssertionError: assert '1000.0 kB' == '1.0 MB'"
    sanitized = sanitize_failure_output(raw_output)
    assert "[HIDDEN - infer this from the fix logic]" in sanitized
    assert "1.0 MB" not in sanitized

def test_extract_python_code_markdown_block():
    llm_response = """
Here is your test:
```python
def test_foo():
    assert True
```
Hope this helps!
"""
    code = extract_python_code(llm_response)
    assert code == "def test_foo():\n    assert True"
