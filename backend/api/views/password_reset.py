# Framework-generated: 0%
# Human-written: 0%
# AI-generated: 100%

"""
Password Reset Views.

This module provides endpoints for password reset functionality:
- POST /auth/password/reset/request/  - Request password reset email
- POST /auth/password/reset/verify/   - Verify reset token is valid
- POST /auth/password/reset/confirm/  - Reset password with token

Security features:
- Tokens are hashed before storage
- Tokens expire after configurable time (default 24 hours)
- Single-use tokens (invalidated after use)
- No email enumeration (always returns success)
"""

import secrets
import hashlib
from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

User = get_user_model()


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def generate_reset_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def store_reset_token(user_id: str, token_hash: str, expiry_hours: int = 24):
    """
    Store password reset token in cache.
    
    Uses Django's cache framework for token storage.
    Token expires after expiry_hours.
    """
    cache_key = f"password_reset:{token_hash}"
    cache_data = {
        'user_id': str(user_id),
        'created_at': timezone.now().isoformat(),
    }
    cache.set(cache_key, cache_data, timeout=expiry_hours * 3600)
    
    # Also store reverse lookup to invalidate old tokens
    user_key = f"password_reset_user:{user_id}"
    old_token_hash = cache.get(user_key)
    if old_token_hash:
        cache.delete(f"password_reset:{old_token_hash}")
    cache.set(user_key, token_hash, timeout=expiry_hours * 3600)


def verify_reset_token(token: str):
    """
    Verify a password reset token.
    
    Returns user_id if valid, None otherwise.
    """
    token_hash = hash_token(token)
    cache_key = f"password_reset:{token_hash}"
    cache_data = cache.get(cache_key)
    
    if cache_data:
        return cache_data.get('user_id')
    return None


def invalidate_reset_token(token: str):
    """Invalidate a password reset token after use."""
    token_hash = hash_token(token)
    cache_key = f"password_reset:{token_hash}"
    cache_data = cache.get(cache_key)
    
    if cache_data:
        user_id = cache_data.get('user_id')
        cache.delete(cache_key)
        cache.delete(f"password_reset_user:{user_id}")
        return True
    return False


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Request a password reset email.
    
    POST /auth/password/reset/request/
    
    Body:
        email: User's email address
    
    Returns:
        200: Always returns success to prevent email enumeration
    
    Security: Always returns success even if email doesn't exist.
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Always return success to prevent email enumeration
    success_response = Response({
        'message': 'If an account exists with this email, a password reset link has been sent.'
    })
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Return success anyway to prevent enumeration
        return success_response
    
    # Generate and store reset token
    token = generate_reset_token()
    token_hash = hash_token(token)
    expiry_hours = getattr(settings, 'PASSWORD_RESET_EXPIRY_HOURS', 24)
    store_reset_token(str(user.pk), token_hash, expiry_hours)
    
    # Build reset URL
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    reset_url = f"{frontend_url}/reset-password?token={token}"
    
    # Send email
    try:
        subject = 'Password Reset Request - PlanningJam'
        message = f"""
Hello {user.username},

You requested a password reset for your PlanningJam account.

Click here to reset your password:
{reset_url}

This link will expire in {expiry_hours} hours.

If you didn't request this, please ignore this email.

- The PlanningJam Team
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@planningjam.com'),
            recipient_list=[user.email],
            fail_silently=True  # Don't expose email errors
        )
    except Exception:
        # Log error but don't expose to user
        pass
    
    return success_response


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def verify_password_reset_token(request):
    """
    Verify that a password reset token is valid.
    
    POST /auth/password/reset/verify/
    
    Body:
        token: Password reset token from email
    
    Returns:
        200: { valid: true } if token is valid
        400: { valid: false, error: "..." } if invalid
    """
    token = request.data.get('token', '')
    
    if not token:
        return Response(
            {'valid': False, 'error': 'Token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_id = verify_reset_token(token)
    
    if user_id:
        # Verify user still exists
        try:
            User.objects.get(pk=user_id)
            return Response({
                'valid': True,
                'message': 'Token is valid'
            })
        except User.DoesNotExist:
            pass
    
    return Response(
        {'valid': False, 'error': 'Invalid or expired token'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Reset password using a valid token.
    
    POST /auth/password/reset/confirm/
    
    Body:
        token: Password reset token from email
        password: New password
        password_confirm: Confirm new password
    
    Returns:
        200: Password reset successful
        400: Invalid token or password validation failed
    """
    token = request.data.get('token', '')
    password = request.data.get('password', '')
    password_confirm = request.data.get('password_confirm', '')
    
    # Validate inputs
    if not token:
        return Response(
            {'error': 'Token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not password or not password_confirm:
        return Response(
            {'error': 'Password and password confirmation are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if password != password_confirm:
        return Response(
            {'error': 'Passwords do not match'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify token
    user_id = verify_reset_token(token)
    if not user_id:
        return Response(
            {'error': 'Invalid or expired token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get user
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate password strength
    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response(
            {'error': list(e.messages)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Reset password
    user.set_password(password)
    user.save()
    
    # Invalidate token (single use)
    invalidate_reset_token(token)
    
    return Response({
        'message': 'Password reset successful. You can now log in with your new password.'
    })
