"""Rate limiter configuration module.

This module is separate from main.py to avoid circular imports when routers
need to access the limiter.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter - imported by routers and main.py
limiter = Limiter(key_func=get_remote_address)
