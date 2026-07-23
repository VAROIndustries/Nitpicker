import re
import amb
from amb import about


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", amb.__version__)


def test_about_exposes_version_and_varo_link():
    assert about.__version__ == amb.__version__
    assert "varo.industries" in about.TOOL_URL
