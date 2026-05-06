"""Test configuration : ajoute le pipeline au sys.path pour les imports."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
