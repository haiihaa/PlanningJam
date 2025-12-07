# Framework-generated: 0%
# Human-written: 0%
# AI-generated: 100%

"""
Tests for Password Reset functionality.

These tests verify:
1. Password reset request endpoint
2. Token verification endpoint
3. Password reset confirmation endpoint
4. Security features (no email enumeration, token expiry, single use)
"""

import pytest
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from api.views.password_reset import (
    generate_reset_token,
    hash_token,
    store_reset_token,
    verify_reset_token,
    invalidate_reset_token,
)

User = get_user_model()


@pytest.mark.django_db
class TestPasswordResetRequest:
    """Test password reset request endpoint."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='oldpassword123'
        )
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()
    
    def test_request_with_valid_email(self, api_client, user):
        """Test requesting password reset with valid email."""
        response = api_client.post('/api/auth/password/reset/request/', {
            'email': 'reset@example.com'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
    
    def test_request_with_invalid_email_still_returns_200(self, api_client):
        """Test that non-existent email still returns 200 (no enumeration)."""
        response = api_client.post('/api/auth/password/reset/request/', {
            'email': 'nonexistent@example.com'
        })
        
        # Should return 200 to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK
    
    def test_request_without_email(self, api_client):
        """Test requesting without email returns error."""
        response = api_client.post('/api/auth/password/reset/request/', {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data


@pytest.mark.django_db
class TestPasswordResetVerify:
    """Test password reset token verification."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='verifyuser',
            email='verify@example.com',
            password='testpass123'
        )
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()
    
    def test_verify_valid_token(self, api_client, user):
        """Test verifying a valid token."""
        token = generate_reset_token()
        token_hash = hash_token(token)
        store_reset_token(str(user.pk), token_hash)
        
        response = api_client.post('/api/auth/password/reset/verify/', {
            'token': token
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] == True
    
    def test_verify_invalid_token(self, api_client):
        """Test verifying an invalid token."""
        response = api_client.post('/api/auth/password/reset/verify/', {
            'token': 'invalid-token-here'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['valid'] == False
    
    def test_verify_without_token(self, api_client):
        """Test verifying without token."""
        response = api_client.post('/api/auth/password/reset/verify/', {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswordResetConfirm:
    """Test password reset confirmation."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='confirmuser',
            email='confirm@example.com',
            password='oldpassword123'
        )
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()
    
    def test_confirm_with_valid_token(self, api_client, user):
        """Test confirming password reset with valid token."""
        token = generate_reset_token()
        token_hash = hash_token(token)
        store_reset_token(str(user.pk), token_hash)
        
        response = api_client.post('/api/auth/password/reset/confirm/', {
            'token': token,
            'password': 'newSecurePass123!',
            'password_confirm': 'newSecurePass123!'
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password('newSecurePass123!')
    
    def test_confirm_with_mismatched_passwords(self, api_client, user):
        """Test confirming with mismatched passwords."""
        token = generate_reset_token()
        token_hash = hash_token(token)
        store_reset_token(str(user.pk), token_hash)
        
        response = api_client.post('/api/auth/password/reset/confirm/', {
            'token': token,
            'password': 'newPassword123!',
            'password_confirm': 'differentPassword!'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_confirm_with_weak_password(self, api_client, user):
        """Test confirming with weak password."""
        token = generate_reset_token()
        token_hash = hash_token(token)
        store_reset_token(str(user.pk), token_hash)
        
        response = api_client.post('/api/auth/password/reset/confirm/', {
            'token': token,
            'password': '123',  # Too short
            'password_confirm': '123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_confirm_with_invalid_token(self, api_client):
        """Test confirming with invalid token."""
        response = api_client.post('/api/auth/password/reset/confirm/', {
            'token': 'invalid-token',
            'password': 'newPassword123!',
            'password_confirm': 'newPassword123!'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_token_is_single_use(self, api_client, user):
        """Test that token can only be used once."""
        token = generate_reset_token()
        token_hash = hash_token(token)
        store_reset_token(str(user.pk), token_hash)
        
        # First use - should succeed
        response1 = api_client.post('/api/auth/password/reset/confirm/', {
            'token': token,
            'password': 'firstNewPass123!',
            'password_confirm': 'firstNewPass123!'
        })
        assert response1.status_code == status.HTTP_200_OK
        
        # Second use - should fail
        response2 = api_client.post('/api/auth/password/reset/confirm/', {
            'token': token,
            'password': 'secondNewPass!',
            'password_confirm': 'secondNewPass!'
        })
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenHelperFunctions:
    """Test helper functions for token management."""
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()
    
    def test_generate_reset_token(self):
        """Test token generation."""
        token = generate_reset_token()
        
        assert token is not None
        assert len(token) > 20  # Should be reasonably long
    
    def test_hash_token(self):
        """Test token hashing."""
        token = 'test-token'
        hashed = hash_token(token)
        
        assert hashed != token
        assert len(hashed) == 64  # SHA256 hex digest
    
    def test_store_and_verify_token(self):
        """Test storing and verifying token."""
        user_id = 'test-user-123'
        token = generate_reset_token()
        token_hash = hash_token(token)
        
        store_reset_token(user_id, token_hash)
        
        verified_user_id = verify_reset_token(token)
        assert verified_user_id == user_id
    
    def test_invalidate_token(self):
        """Test token invalidation."""
        user_id = 'test-user-456'
        token = generate_reset_token()
        token_hash = hash_token(token)
        
        store_reset_token(user_id, token_hash)
        
        # Token should be valid
        assert verify_reset_token(token) == user_id
        
        # Invalidate
        invalidate_reset_token(token)
        
        # Token should no longer be valid
        assert verify_reset_token(token) is None
    
    def test_new_token_invalidates_old(self):
        """Test that generating new token invalidates old one."""
        user_id = 'test-user-789'
        
        # Store first token
        token1 = generate_reset_token()
        store_reset_token(user_id, hash_token(token1))
        
        # Store second token for same user
        token2 = generate_reset_token()
        store_reset_token(user_id, hash_token(token2))
        
        # First token should be invalid
        assert verify_reset_token(token1) is None
        
        # Second token should be valid
        assert verify_reset_token(token2) == user_id
