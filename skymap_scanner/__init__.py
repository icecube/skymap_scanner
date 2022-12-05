"""Init."""

# isort: skip_file

# NOTE:
#  MQClient needs to be the *FIRST* import so C++ bindings can be made ASAP
#  before any other dependency. Previously, there were issues when this
#  was preceded by `import healpy`.
import mqclient

# version is a human-readable version number.

# version_info is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)
__version__ = "3.0.57"
version_info = (
    int(__version__.split(".")[0]),
    int(__version__.split(".")[1]),
    int(__version__.split(".")[2]),
    0,
)
