import pytest
import sys

class OutputCapture:
    def __init__(self):
        self.lines = []
    def write(self, s):
        if s.strip():
            self.lines.append(s.strip())
    def flush(self):
        pass
    def isatty(self):
        return False
    def fileno(self):
        return 1

capture = OutputCapture()
old_stdout = sys.stdout
sys.stdout = capture

ret = pytest.main(["-q", "--no-header"])

sys.stdout = old_stdout
summary_lines = [l for l in capture.lines if "passed" in l or "failed" in l or "error" in l]
print("Pytest Return Code:", ret)
print("Summary Line:", summary_lines[-1] if summary_lines else "No summary")
for l in capture.lines[-15:]:
    print("  ->", l)