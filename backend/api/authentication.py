# Framework-generated: 0%
# Human-written: 0%
# AI-generated: 100%
#   - Secure HttpOnly cookie-based JWT authentication

"""
Custom JWT Authentication using HttpOnly cookies.

This module provides secure token storage by reading JWT tokens from
HttpOnly cookies instead of Authorization headers, protecting against
XSS attacks. The access token is stored in a secure, HttpOnly cookie
that JavaScript cannot access.

Security features:
- HttpOnly: Prevents JavaScript access to tokens
- Secure: Only sent over HTTPS in production
- SameSite: Protects against CSRF attacks
- Short-lived access tokens with refresh capability
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from HttpOnly cookies.
    
    This authentication class extends the default JWTAuthentication to
    read the access token from an HttpOnly cookie instead of the
    Authorization header. This protects against XSS attacks since
    JavaScript cannot access HttpOnly cookies.
    
    Falls back to header-based authentication for API clients that
    cannot use cookies (e.g., mobile apps, third-party integrations).
    """
    
    def authenticate(self, request: Request):
        """
        Authenticate the request using JWT from cookies or headers.
        
        Priority:
        1. Try to get token from HttpOnly cookie
        2. Fall back to Authorization header (for backward compatibility)
        
        Returns:
            Tuple of (user, validated_token) if authentication succeeds
            None if no token is present
            
        Raises:
            InvalidToken: If token is present but invalid
        """
        # First, try to get token from cookie
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        
        if raw_token is not None:
            try:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                return (user, validated_token)
            except TokenError as e:
                logger.warning(f"Invalid token in cookie: {e}")
                # Token in cookie is invalid, don't fall back to header
                # to prevent confusion about which token is being used
                raise InvalidToken(e.args[0])
        
        # Fall back to header-based authentication for API clients
        # that cannot use cookies (mobile apps, etc.)
        return super().authenticate(request)


def get_tokens_for_user(user) -> dict:
    """
    Generate access and refresh tokens for a user.
    
    Args:
        user: Django user instance
        
    Returns:
        Dictionary with 'access' and 'refresh' token strings
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def set_jwt_cookies(response, access_token: str, refresh_token: str = None):
    """
    Set JWT tokens as HttpOnly cookies on the response.
    
    Args:
        response: Django/DRF response object
        access_token: JWT access token string
        refresh_token: JWT refresh token string (optional)
        
    Returns:
        Modified response with cookies set
    """
    # Access token cookie
    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE,
        value=access_token,
        max_age=settings.JWT_AUTH_COOKIE_MAX_AGE,
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
        path='/',
    )
    
    # Refresh token cookie (separate cookie for security)
    if refresh_token:
        response.set_cookie(
            key=settings.JWT_AUTH_REFRESH_COOKIE,
            value=refresh_token,
            max_age=settings.JWT_AUTH_REFRESH_COOKIE_MAX_AGE,
            secure=settings.JWT_AUTH_COOKIE_SECURE,
            httponly=True,
            samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
            path='/api/token/',  # Only sent to token endpoints
        )
    
    return response


def clear_jwt_cookies(response):
    """
    Clear JWT cookies from the response (for logout).
    
    Args:
        response: Django/DRF response object
        
    Returns:
        Modified response with cookies cleared
    """
    response.delete_cookie(
        key=settings.JWT_AUTH_COOKIE,
        path='/',
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.JWT_AUTH_REFRESH_COOKIE,
        path='/api/token/',
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
    )
    
    return response
