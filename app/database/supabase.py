"""
Supabase client module.

Initializes and exposes singleton Supabase clients for use throughout the backend.
Two clients are provided:

- anon_client: uses the public anonymous key, suitable for user-scoped operations.
- service_client: uses the service-role key, suitable for privileged server-side operations.

Clients are created once at module load time and reused on every call.
"""

import logging
import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

_SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
_SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
_SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_missing: list[str] = [
    name
    for name, value in (
        ("SUPABASE_URL", _SUPABASE_URL),
        ("SUPABASE_ANON_KEY", _SUPABASE_ANON_KEY),
        ("SUPABASE_SERVICE_ROLE_KEY", _SUPABASE_SERVICE_ROLE_KEY),
    )
    if not value
]

if _missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Ensure these are set in your .env file or execution environment."
    )

# ---------------------------------------------------------------------------
# Singleton client initialization
# ---------------------------------------------------------------------------

anon_client: Client = create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
service_client: Client = create_client(_SUPABASE_URL, _SUPABASE_SERVICE_ROLE_KEY)

logger.info("Supabase clients initialized successfully.")

# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def get_anon_client() -> Client:
    """Return the singleton anonymous Supabase client."""
    return anon_client


def get_service_client() -> Client:
    """Return the singleton service-role Supabase client."""
    return service_client
