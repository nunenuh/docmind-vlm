"""Placeholder test to ensure pytest collects at least one test."""


def test_scaffold_exists():
    """Verify the scaffold is importable."""
    from docmind.main import app

    assert app is not None
