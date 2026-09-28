"""Run deterministic tests, including the real framework with scripted model replies."""
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    raise SystemExit(subprocess.call([sys.executable, '-m', 'pytest', '-q'], cwd=Path(__file__).resolve().parents[1]))
