"""Test that skills subparser doesn't conflict (regression test for #898)."""

import argparse
import importlib
import sys


def test_no_duplicate_skills_subparser():
    """Ensure 'skills' subparser is only registered once to avoid Python 3.11+ crash.

    Python 3.11 changed argparse to raise an exception on duplicate subparser
    names instead of silently overwriting (see CPython #94331).

    This test will fail with:
        argparse.ArgumentError: argument command: conflicting subparser: skills

    if the duplicate 'skills' registration is reintroduced.
    """
    # Import through the canonical cache so collection cannot fork hermes_cli.main.
    package = importlib.import_module("hermes_cli")
    missing = object()
    previous_module = sys.modules.get("hermes_cli.main", missing)
    previous_attribute = getattr(package, "main", missing)
    try:
        imported = importlib.import_module("hermes_cli.main")
        assert sys.modules["hermes_cli.main"] is imported
        assert sys.modules["hermes_cli.main"] is package.main
    except argparse.ArgumentError as e:
        if "conflicting subparser" in str(e):
            raise AssertionError(
                f"Duplicate subparser detected: {e}. "
                "See issue #898 for details."
            ) from e
        raise
    finally:
        # Restore both references so this import check cannot pollute later tests.
        if previous_module is missing:
            sys.modules.pop("hermes_cli.main", None)
        else:
            sys.modules["hermes_cli.main"] = previous_module
        if previous_attribute is missing:
            if hasattr(package, "main"):
                delattr(package, "main")
        else:
            package.main = previous_attribute
