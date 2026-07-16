"""Test configuration — ensures ai-team root is on sys.path."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
