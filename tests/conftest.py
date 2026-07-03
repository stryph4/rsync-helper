import os
import sys


def pytest_configure(config):
    # Ensure tests can import the package when running from tests/ or subdirs
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
