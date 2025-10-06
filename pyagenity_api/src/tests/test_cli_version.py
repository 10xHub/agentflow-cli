import re

from pyagenity_api.cli.commands.version import VersionCommand
from pyagenity_api.cli.constants import CLI_VERSION

SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")


class StubOutput:
    def __init__(self):
        self.banner_args = []
        self.success_messages = []
        self.info_messages = []
        self.error_messages = []

    # Methods used by VersionCommand
    def print_banner(self, title, subtitle, color=""):
        self.banner_args.append((title, subtitle, color))

    def success(self, msg):
        self.success_messages.append(msg)

    def info(self, msg):
        self.info_messages.append(msg)

    # For error handling path (not expected here)
    def error(self, msg):
        self.error_messages.append(msg)


def test_version_command_outputs_versions():
    stub = StubOutput()
    cmd = VersionCommand(output=stub)  # type: ignore[arg-type]
    exit_code = cmd.execute()
    assert exit_code == 0

    # Banner printed once with expected title
    assert stub.banner_args, "Banner not printed"
    title, subtitle, _ = stub.banner_args[0]
    assert title == "Version"
    assert "version info" in subtitle.lower()

    # Success message contains CLI version
    assert any(CLI_VERSION in m for m in stub.success_messages), stub.success_messages
    # Extract package version from info messages (may contain multiple lines)
    joined_info = "\n".join(stub.info_messages)
    semvers = SEMVER_RE.findall(joined_info)
    # At least one semantic version should be present (package version)
    assert semvers, f"No semantic version found in info messages: {joined_info}"
