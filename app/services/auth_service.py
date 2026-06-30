"""
Authentication service module.

Handles business logic for user signup and login via Supabase.
Operates independently of FastAPI (no Request, no HTTP middleware).
"""

import logging

from app.database.supabase import get_anon_client, get_service_client

logger = logging.getLogger(__name__)


def signup(email: str, password: str, organization_id: str, role: str) -> dict[str, str]:
    """
    Creates a new user via Supabase Auth and inserts their profile into the public.users table.
    
    Checks organization existence first to prevent orphan auth accounts.
    Uses the service_client to insert the user profile since RLS blocks unauthenticated inserts.
    """
    if role not in ("admin", "member"):
        logger.warning("Signup failed: Invalid role '%s' requested.", role)
        raise ValueError("Invalid role. Must be 'admin' or 'member'.")

    anon_client = get_anon_client()
    service_client = get_service_client()

    # 1. Verify organization exists using service_client (bypasses RLS)
    try:
        org_res = service_client.table("organizations").select("id").eq("id", organization_id).execute()
        if not org_res.data:
            logger.warning("Signup failed: Organization %s does not exist.", organization_id)
            raise ValueError("Organization does not exist.")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        logger.warning("Signup failed during organization check: %s", str(e))
        raise ValueError("Organization does not exist or invalid ID.")

    # 2. Create user in Supabase Auth
    try:
        auth_res = anon_client.auth.sign_up({"email": email, "password": password})
        if not auth_res.user:
            logger.error("Signup failed: No user returned by Supabase Auth.")
            raise RuntimeError("Signup failed: Internal error during user creation.")
        user_id = auth_res.user.id
    except Exception as e:
        err_msg = str(e).lower()
        if "already registered" in err_msg or "already exists" in err_msg or "user already exists" in err_msg:
            logger.warning("Signup failed: Email already exists.")
            raise ValueError("Email already exists.")
        
        # If Supabase Auth rejects the email (e.g. invalid format, blocked role email, or rate limits)
        # we should return a 400 Bad Request to the user instead of a 500 Internal Server Error.
        if type(e).__name__ == "AuthApiError":
            logger.warning("Signup rejected by Supabase Auth: %s", str(e))
            raise ValueError(str(e))
            
        logger.error("Signup failed during Supabase Auth: %s", str(e))
        raise RuntimeError(f"Failed to create user: {str(e)}")

    # 3. Insert profile into public.users using service_client
    try:
        service_client.table("users").insert({
            "id": user_id,
            "organization_id": organization_id,
            "role": role
        }).execute()
    except Exception as e:
        logger.error("Signup failed: Could not create user profile for %s. Error: %s", user_id, str(e))
        try:
            service_client.auth.admin.delete_user(user_id)
            logger.info("Rollback: Deleted orphan Auth user %s after profile insert failure.", user_id)
        except Exception as cleanup_error:
            logger.error("Rollback failed: Could not delete orphan Auth user %s. Error: %s", user_id, str(cleanup_error))
        raise RuntimeError(f"Failed to create user profile: {str(e)}")

    # 4. Update app_metadata on the Auth user via service_client
    try:
        service_client.auth.admin.update_user_by_id(
            user_id,
            {"app_metadata": {"role": role, "org_id": organization_id}}
        )
    except Exception as e:
        logger.error("Signup failed: Could not update app_metadata for %s. Error: %s", user_id, str(e))
        try:
            service_client.auth.admin.delete_user(user_id)
            logger.info("Rollback: Deleted Auth user %s after app_metadata update failure.", user_id)
        except Exception as cleanup_error:
            logger.error("Rollback failed: Could not delete Auth user %s. Error: %s", user_id, str(cleanup_error))
        raise RuntimeError(f"Failed to update user metadata: {str(e)}")

    logger.info("Signup successful for user %s in organization %s.", user_id, organization_id)
    return {"message": "User created successfully."}


def login(email: str, password: str) -> dict[str, str | int]:
    """
    Authenticates a user via Supabase Auth and returns the JWT tokens.
    """
    anon_client = get_anon_client()

    try:
        response = anon_client.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })
        session = response.session
        if not session:
            logger.error("Login failed: No session returned by Supabase Auth.")
            raise RuntimeError("Login failed: Internal error retrieving session.")
            
        logger.info("Login successful for user %s.", response.user.id)
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": session.token_type,
            "expires_in": session.expires_in,
            "user_id": response.user.id
        }
    except Exception as e:
        err_msg = str(e).lower()
        if "invalid login credentials" in err_msg or "invalid credentials" in err_msg:
            logger.warning("Login failed: Invalid credentials provided.")
            raise ValueError("Invalid credentials.")
        
        logger.error("Login failed due to unexpected error: %s", str(e))
        raise RuntimeError(f"Authentication failed: {str(e)}")
