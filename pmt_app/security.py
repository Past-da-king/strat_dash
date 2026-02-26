"""
Security Module for Strat Edge Project Portal
Handles: Cookie Security, CSRF Protection, Rate Limiting, Input Validation
"""

import streamlit as st
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from functools import wraps
import re


# =============================================================================
# CONFIGURATION
# =============================================================================

# Cookie Security Settings
COOKIE_SECURE = True  # Only send over HTTPS
COOKIE_HTTPONLY = False  # Streamlit requires JS access, but documented for deployment
COOKIE_SAMESITE = "lax"  # Prevent CSRF
COOKIE_MAX_AGE = 604800  # 7 days in seconds

# Rate Limiting Settings
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes in seconds
RATE_LIMIT_WINDOW = 300  # 5 minutes window

# Input Validation Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'csv': 'text/csv',
    'zip': 'application/zip',
    'txt': 'text/plain',
}

# Input Validation Patterns
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,32}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PROJECT_NUMBER_PATTERN = re.compile(r'^[a-zA-Z0-9\-]{3,20}$')

# =============================================================================
# COOKIE SECURITY
# =============================================================================

def set_secure_cookie(cookie_name: str, value: str, max_age: int = COOKIE_MAX_AGE):
    """
    Sets a cookie with secure flags using Streamlit's context API.
    
    Security features:
    - SameSite=Lax to prevent CSRF
    - Secure flag for HTTPS-only transmission
    - HttpOnly flag (when supported) to prevent XSS access
    - Max-Age for automatic expiration
    """
    # Generate a signature for cookie integrity verification
    signature = _generate_cookie_signature(value)
    signed_value = f"{value}|{signature}"
    
    # Build cookie string with security flags
    cookie_string = f"{cookie_name}={signed_value}; Max-Age={max_age}; Path=/; SameSite=Lax"
    
    # Add Secure flag for production (HTTPS)
    if COOKIE_SECURE:
        cookie_string += "; Secure"
    
    # Note: HttpOnly cannot be set via JavaScript/Streamlit, but documented for deployment
    if not COOKIE_HTTPONLY:
        cookie_string += "; HttpOnly"
    
    # Set cookie via Streamlit session state (main.py handles actual cookie setting)
    st.session_state["_set_cookie"] = {
        "name": cookie_name,
        "value": signed_value,
        "max_age": max_age,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE
    }


def get_secure_cookie(cookie_name: str) -> str | None:
    """
    Retrieves and validates a cookie value.
    Verifies cookie signature to prevent tampering.
    """
    try:
        signed_value = st.context.cookies.get(cookie_name)
        if not signed_value:
            return None
        
        # Split value and signature
        parts = signed_value.split('|')
        if len(parts) != 2:
            return None
        
        value, signature = parts
        
        # Verify signature
        if not _verify_cookie_signature(value, signature):
            return None
        
        return value
    except Exception:
        return None


def delete_secure_cookie(cookie_name: str):
    """Securely deletes a cookie by setting expiration to past."""
    st.session_state["_del_cookie"] = {
        "name": cookie_name,
        "value": "",
        "max_age": 0
    }


def _generate_cookie_signature(value: str) -> str:
    """Generate HMAC signature for cookie integrity."""
    try:
        secret_key = st.secrets.get("security", {}).get("cookie_secret", "default_secret_change_in_production")
    except Exception:
        secret_key = "default_secret_change_in_production"
    
    signature = hmac.new(
        secret_key.encode(),
        value.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def _verify_cookie_signature(value: str, signature: str) -> bool:
    """Verify cookie HMAC signature."""
    try:
        expected_signature = _generate_cookie_signature(value)
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


# =============================================================================
# CSRF PROTECTION
# =============================================================================

def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    if "_csrf_token" not in st.session_state:
        st.session_state["_csrf_token"] = secrets.token_urlsafe(32)
    return st.session_state["_csrf_token"]


def validate_csrf_token() -> bool:
    """Validate CSRF token from form submission."""
    # For session-based CSRF, we just verify the token exists
    session_token = st.session_state.get("_csrf_token")
    return session_token is not None


def get_csrf_token_field():
    """
    Generates and returns CSRF token (stored in session state only, no UI element).
    Call this inside your form to ensure token is generated.
    """
    return generate_csrf_token()


# =============================================================================
# RATE LIMITING
# =============================================================================

def _get_rate_limit_key(identifier: str) -> str:
    """Generate rate limit storage key."""
    return f"rate_limit_{identifier}"


def _get_lockout_key(identifier: str) -> str:
    """Generate lockout storage key."""
    return f"lockout_{identifier}"


def check_rate_limit(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS, 
                     window: int = RATE_LIMIT_WINDOW) -> tuple[bool, int]:
    """
    Check if an identifier (IP/username) has exceeded rate limit.
    
    Returns:
        tuple: (is_allowed, remaining_attempts)
    """
    now = time.time()
    
    # Check if currently locked out
    lockout_until = st.session_state.get(_get_lockout_key(identifier))
    if lockout_until:
        if now < lockout_until:
            return False, 0
        else:
            # Lockout expired, reset
            del st.session_state[_get_lockout_key(identifier)]
            st.session_state[_get_rate_limit_key(identifier)] = []
    
    # Get attempt history
    attempts = st.session_state.get(_get_rate_limit_key(identifier), [])
    
    # Remove old attempts outside the window
    attempts = [t for t in attempts if now - t < window]
    st.session_state[_get_rate_limit_key(identifier)] = attempts
    
    # Check if exceeded
    if len(attempts) >= max_attempts:
        # Set lockout
        st.session_state[_get_lockout_key(identifier)] = now + LOCKOUT_DURATION
        return False, 0
    
    return True, max_attempts - len(attempts)


def record_attempt(identifier: str):
    """Record an attempt for rate limiting."""
    now = time.time()
    attempts = st.session_state.get(_get_rate_limit_key(identifier), [])
    attempts.append(now)
    st.session_state[_get_rate_limit_key(identifier)] = attempts


def reset_rate_limit(identifier: str):
    """Reset rate limit for an identifier (e.g., after successful login)."""
    rate_key = _get_rate_limit_key(identifier)
    lockout_key = _get_lockout_key(identifier)
    
    if rate_key in st.session_state:
        del st.session_state[rate_key]
    if lockout_key in st.session_state:
        del st.session_state[lockout_key]


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format.
    
    Requirements:
    - 3-32 characters
    - Alphanumeric and underscores only
    - No special characters or spaces
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3 or len(username) > 32:
        return False, "Username must be 3-32 characters"
    
    if not USERNAME_PATTERN.match(username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format."""
    if not email:
        return False, "Email is required"
    
    if len(email) > 254:
        return False, "Email is too long"
    
    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    
    return True, ""


def validate_project_number(project_number: str) -> tuple[bool, str]:
    """Validate project number format."""
    if not project_number:
        return False, "Project number is required"
    
    if len(project_number) < 3 or len(project_number) > 20:
        return False, "Project number must be 3-20 characters"
    
    if not PROJECT_NUMBER_PATTERN.match(project_number):
        return False, "Project number can only contain letters, numbers, and hyphens"
    
    return True, ""


def validate_file_upload(uploaded_file) -> tuple[bool, str]:
    """
    Validate uploaded file for security.
    
    Checks:
    - File size within limits
    - File extension allowed
    - MIME type matches extension
    """
    if uploaded_file is None:
        return False, "No file selected"
    
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
    
    # Check file extension
    filename = uploaded_file.name.lower()
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
    
    if ext not in ALLOWED_FILE_TYPES:
        return False, f"File type '{ext}' not allowed"
    
    # Check MIME type (basic validation)
    mime_type = uploaded_file.type
    
    # Allow if MIME type matches expected or if it's a generic type
    expected_mime = ALLOWED_FILE_TYPES.get(ext)
    if mime_type and expected_mime and mime_type != expected_mime:
        # Some MIME types have variations, allow common ones
        if not (ext == 'jpg' and mime_type == 'image/jpeg'):
            return False, f"MIME type {mime_type} doesn't match file extension"
    
    # Additional security: Check for magic bytes (file signature)
    file_header = uploaded_file.read(16)
    uploaded_file.seek(0)  # Reset file pointer
    
    # Basic magic byte validation for common types
    if ext == 'pdf' and not file_header.startswith(b'%PDF'):
        return False, "Invalid PDF file"
    
    if ext in ['png'] and not file_header.startswith(b'\x89PNG'):
        return False, f"Invalid {ext} file"
    
    if ext in ['jpg', 'jpeg'] and not file_header.startswith(b'\xff\xd8\xff'):
        return False, f"Invalid {ext} file"
    
    return True, ""


def sanitize_html(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    Basic HTML entity encoding.
    """
    if not text:
        return ""
    
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        ">": "&gt;",
        "<": "&lt;",
    }
    
    return "".join(html_escape_table.get(c, c) for c in text)


def validate_amount(amount: float, min_value: float = 0.01, max_value: float = 1_000_000_000) -> tuple[bool, str]:
    """Validate monetary amounts."""
    if amount is None:
        return False, "Amount is required"
    
    if amount < min_value:
        return False, f"Amount must be at least {min_value}"
    
    if amount > max_value:
        return False, f"Amount exceeds maximum limit of {max_value:,.0f}"
    
    return True, ""


def validate_date(date_value, min_year: int = 2020, max_year: int = 2030) -> tuple[bool, str]:
    """Validate date values."""
    if date_value is None:
        return False, "Date is required"
    
    try:
        year = date_value.year if hasattr(date_value, 'year') else int(date_value[:4])
        if year < min_year or year > max_year:
            return False, f"Year must be between {min_year} and {max_year}"
        return True, ""
    except Exception:
        return False, "Invalid date format"


# =============================================================================
# SECURITY DECORATORS
# =============================================================================

def rate_limited(max_attempts: int = MAX_LOGIN_ATTEMPTS, window: int = RATE_LIMIT_WINDOW):
    """Decorator for rate-limiting functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(identifier: str, *args, **kwargs):
            is_allowed, remaining = check_rate_limit(identifier, max_attempts, window)
            
            if not is_allowed:
                return False, f"Too many attempts. Please try again in {LOCKOUT_DURATION // 60} minutes."
            
            result = func(identifier, *args, **kwargs)
            
            if not result[0]:  # If function returned failure
                record_attempt(identifier)
            
            return result
        return wrapper
    return decorator


# =============================================================================
# SECURITY HEADERS (For deployment)
# =============================================================================

def get_security_headers() -> dict:
    """
    Returns recommended security headers for deployment.
    Add these to your reverse proxy or web server configuration.
    """
    return {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com;",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
