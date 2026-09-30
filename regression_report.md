# Regression Guard Report

## Bug Diff

diff --git a/src/humanize/filesize.py b/src/humanize/filesize.py
index c495fed..315261a 100644
--- a/src/humanize/filesize.py
+++ b/src/humanize/filesize.py
@@ -97,6 +97,12 @@ def naturalsize(
         return f"{int(bytes_)}B" if gnu else _("%d Bytes") % int(bytes_)
 
     exp = int(min(log(abs_bytes, base), len(suffix)))
+    # The suffix is chosen from the unrounded byte count, but `format` rounds the
+    # mantissa afterward; rounding can push it up to `base` (e.g. 999999 is
+    # 999.999 kB, which formats to "1000.0 kB"). When that happens and a larger
+    # suffix is available, step up one suffix so the result reads "1.0 MB".
+    if exp < len(suffix) and abs(float(format % (abs_bytes / (base**exp)))) >= base:
+        exp += 1
     space = "" if gnu else " "
     ret: str = format % (bytes_ / (base**exp)) + space + _(suffix[exp - 1])
     return ret
diff --git a/tests/test_filesize.py b/tests/test_filesize.py
index 04774d9..e695639 100644
--- a/tests/test_filesize.py
+++ b/tests/test_filesize.py
@@ -82,6 +82,15 @@ import humanize
         ([1.123456789, False, True], "1B"),
         ([1.123456789 * 10**3, False, True], "1.1K"),
         ([1.123456789 * 10**6, False, True], "1.1M"),
+        # Rounding must not leave the mantissa at the base while a larger suffix
+        # is available: 999999 is 999.999 kB, which the "%.1f" format rounds to
+        # 1000.0 and must carry into 1.0 MB rather than render as "1000.0 kB".
+        ([999999], "1.0 MB"),
+        ([999999999], "1.0 GB"),
+        ([999999999999], "1.0 TB"),
+        ([1024**2 - 1, True], "1.0 MiB"),
+        ([1024**3 - 1, True], "1.0 GiB"),
+        ([1024**2 - 1, False, True], "1.0M"),
     ],
 )
 def test_naturalsize(test_args: list[int] | list[int | bool], expected: str) -> None:


## Root Cause

The bug was related to the rounding of floating-point numbers. When the format function was used, it could round the mantissa (the fractional part) of the result to the base (e.g. kilobyte, megabyte, etc.) without leaving any remainder. This could lead to unexpected results, such as "1000.0 kB" instead of "999.999 kB". The fix changed the behavior to step up to the next suffix when this happened, ensuring that the result is displayed with the correct suffix.

## Accepted Regression Test

```python
import humanize.filesize

def test_boundary_suffix():
    assert humanize.filesize.naturalsize(999999) == '1.0 MB'
```

## Validation Evidence

### Ran on BUGGY version:
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Sharm\OneDrive\Desktop\production_bug\buggy_workspace
configfile: pyproject.toml (WARNING: ignoring pytest config in tox.ini!)
plugins: anyio-4.11.0
collected 1 item

test_generated.py [31mF[0m[31m                                                      [100%][0m

================================== FAILURES ===================================
[31m[1m____________________________ test_boundary_suffix _____________________________[0m

    [0m[94mdef[39;49;00m[90m [39;49;00m[92mtest_boundary_suffix[39;49;00m():[90m[39;49;00m
>       [94massert[39;49;00m humanize.filesize.naturalsize([94m999999[39;49;00m) == [33m'[39;49;00m[33m1.0 MB[39;49;00m[33m'[39;49;00m[90m[39;49;00m
[1m[31mE       AssertionError: assert '1000.0 kB' == '1.0 MB'[0m
[1m[31mE         [0m
[1m[31mE         [0m[91m- 1.0 MB[39;49;00m[90m[39;49;00m[0m
[1m[31mE         [92m+ 1000.0 kB[39;49;00m[90m[39;49;00m[0m

[1m[31mtest_generated.py[0m:4: AssertionError
[36m[1m=========================== short test summary info ===========================[0m
[31mFAILED[0m test_generated.py::[1mtest_boundary_suffix[0m - AssertionError: assert '1000.0 kB' == '1.0 MB'
[31m============================== [31m[1m1 failed[0m[31m in 0.20s[0m[31m ==============================[0m


### Ran on FIXED version:
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Sharm\OneDrive\Desktop\production_bug\fixed_workspace
configfile: pyproject.toml (WARNING: ignoring pytest config in tox.ini!)
plugins: anyio-4.11.0
collected 1 item

test_generated.py [32m.[0m[32m                                                      [100%][0m

[32m============================== [32m[1m1 passed[0m[32m in 0.03s[0m[32m ==============================[0m


## Conclusion

The above test fails on the buggy version and passes on the fixed version,
confirming this test correctly captures the reported bug.
