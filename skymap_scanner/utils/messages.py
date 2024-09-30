"""Utility functions for interacting with messages."""

import base64
import pickle
from typing import Any


class Serialization:
    """Handling for serializing/deserializing message data."""

    @staticmethod
    def encode_pkl_b64(obj: Any) -> str:
        """Encode a Python object to message-friendly string."""
        return base64.b64encode(pickle.dumps(obj)).decode()

    @staticmethod
    def decode_pkl_b64(b64_string: str) -> Any:
        """Decode a message-friendly to Python object."""
        return pickle.loads(base64.b64decode(b64_string))
