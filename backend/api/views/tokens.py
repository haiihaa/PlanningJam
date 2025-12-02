# Framework-generated: 0%
# Human-written: 0%
# AI-generated: 100% 
#   - Secure HttpOnly cookie-based JWT token views

"""
Secure JWT Token Views with HttpOnly Cookie Support.

These views extend the standard simplejwt views to set tokens in
secure HttpOnly cookies instead of returning them in the response body.
This protects against XSS attacks while maintaining API compatibility.

For backward compatibility with mobile apps or API clients that cannot
use cookies, tokens are still returned in the response body. The frontend
should be updated to NOT store these in localStorage.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from ..authentication import set_jwt_cookies, clear_jwt_cookies


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that sets HttpOnly cookies.
    
    Extends TokenObtainPairView to set access and refresh tokens
    in secure HttpOnly cookies after successful authentication.
    
    Response includes tokens in body for backward compatibility,
    but frontend should NOT store these in localStorage.
    """
    renderer_classes = [JSONRenderer]
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')
            
            if access_token and refresh_token:
                set_jwt_cookies(response, access_token, refresh_token)
                
                # Optionally remove tokens from response body for maximum security
                # Uncomment below if frontend is updated to use cookies only:
                # response.data = {'detail': 'Successfully authenticated'}
        
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view that reads from and sets HttpOnly cookies.
    
    Reads the refresh token from cookies (if available) or request body,
    and sets the new access token in a secure HttpOnly cookie.
    """
    renderer_classes = [JSONRenderer]
    
    def post(self, request, *args, **kwargs):
        # Try to get refresh token from cookie first
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        
        if refresh_token:
            # Use refresh token from cookie
            request_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            request_data['refresh'] = refresh_token
            
            # Temporarily modify request data
            original_data = request._full_data if hasattr(request, '_full_data') else None
            request._full_data = request_data
        
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            raise
        finally:
            # Restore original data if we modified it
            if refresh_token and 'original_data' in locals() and original_data is not None:
                request._full_data = original_data
        
        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get('access')
            
            if access_token:
                # Set new access token cookie
                set_jwt_cookies(response, access_token)
                
                # If we got a rotated refresh token, update that cookie too
                new_refresh_token = response.data.get('refresh')
                if new_refresh_token:
                    set_jwt_cookies(response, access_token, new_refresh_token)
        
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint that clears JWT cookies and blacklists refresh token.
    
    This endpoint:
    1. Clears the access and refresh token cookies
    2. Optionally blacklists the refresh token (if blacklist is enabled)
    
    Returns:
        200: Successfully logged out
        400: Error during logout
    """
    response = Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
    
    # Clear JWT cookies
    clear_jwt_cookies(response)
    
    # Try to blacklist the refresh token if blacklisting is enabled
    refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
    if not refresh_token:
        # Try from request body for backward compatibility
        refresh_token = request.data.get('refresh')
    
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            # Only blacklist if the app is configured for it
            if hasattr(token, 'blacklist'):
                token.blacklist()
        except TokenError:
            # Token is already invalid/expired, that's fine
            pass
    
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_all_view(request):
    """
    Logout endpoint that works without authentication.
    
    This is useful for clearing cookies even when the token is expired
    or invalid. It simply clears the cookies without any validation.
    
    Returns:
        200: Cookies cleared
    """
    response = Response({'detail': 'Logged out'}, status=status.HTTP_200_OK)
    clear_jwt_cookies(response)
    return response


# Legacy views for backward compatibility (can be removed once frontend is updated)
class JSONTokenObtainPairView(TokenObtainPairView):
    """Legacy view - use CookieTokenObtainPairView instead."""
    renderer_classes = [JSONRenderer]


class JSONTokenRefreshView(TokenRefreshView):
    """Legacy view - use CookieTokenRefreshView instead."""
    renderer_classes = [JSONRenderer]