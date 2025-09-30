#!/usr/bin/env python3
"""Simple test script to validate our CLI architecture."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add CLI path directly to avoid main package import issues
cli_path = project_root / "pyagenity_api" / "cli"
sys.path.insert(0, str(cli_path))


def test_imports():
    """Test that our CLI modules can be imported."""
    try:
        # Try importing CLI modules directly without going through main package
        import constants
        import exceptions

        print("✅ CLI constants and exceptions imported")
        print(f"   CLI Version: {constants.CLI_VERSION}")

        # Test core modules
        from core.output import OutputFormatter

        print("✅ Output formatter imported")

        # Test output formatter
        output = OutputFormatter()
        output.success("Test message", emoji=False)
        print("✅ Output formatter working")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_structure():
    """Test the overall CLI structure."""
    try:
        from pyagenity_api.cli.main import app

        print("✅ Main CLI app imported")

        # Test if commands are registered
        commands = app.registered_commands
        print(f"✅ Registered commands: {list(commands.keys())}")

        return True

    except Exception as e:
        print(f"❌ CLI structure test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔬 Testing Professional Pyagenity CLI Architecture")
    print("=" * 50)

    success = True

    print("\n1. Testing imports...")
    success = test_imports() and success

    print("\n2. Testing CLI structure...")
    success = test_cli_structure() and success

    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! CLI architecture is working correctly.")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Please check the output above.")
        sys.exit(1)
