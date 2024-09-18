"""Utility functions for interacting with messages."""

import base64
import pickle
from typing import Any


class MessageData:
    """Handling for message data."""

    @staticmethod
    def encode(data: Any) -> str:
        """Encode a Python object to message-friendly string."""
        return base64.b64encode(pickle.dumps(data)).decode()

    @staticmethod
    def decode(data: str) -> Any:
        """Decode a message-friendly to Python object."""
        return pickle.loads(base64.b64decode(data))
