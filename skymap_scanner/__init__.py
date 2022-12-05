"""Init."""

# isort: skip_file

# NOTE: Import order matters here, due to establishing C++ bindings.
# 1st
try:
    from icecube import recclasses
except ModuleNotFoundError:
    # side note: there's a chance we want to run scanner modules w/out icecube
    pass
# 2nd
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
