"""Test configuration: adds the pipeline to sys.path for imports."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
