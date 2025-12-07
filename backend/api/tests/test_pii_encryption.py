"""
Test PII Encryption Implementation

This file demonstrates multiple ways to test the PII encryption functionality:
1. Unit tests for encryption utilities
2. Integration tests for serializers
3. API endpoint tests
4. Manual testing scripts
"""

import pytest
import json
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from api.utils.encryption import pii_encryption, EncryptionError
from api.models import UserProfile
from api.serializers.auth_serializer import UserRegistrationSerializer, UserSerializer


# =============================================================================
# 1. UNIT TESTS - Test encryption utilities directly
# =============================================================================

class EncryptionUtilsTest(TestCase):
    """Test core encryption functionality"""
    
    def test_string_encryption_roundtrip(self):
        """Test that we can encrypt and decrypt strings"""
        original = "Test String for Encryption"
        encrypted = pii_encryption.encrypt_string(original)
        decrypted = pii_encryption.decrypt_string(encrypted)
        
        # Verify encryption changed the value
        self.assertNotEqual(original, encrypted)
        self.assertGreater(len(encrypted), len(original))
        
        # Verify decryption restored original
        self.assertEqual(original, decrypted)
    
    def test_email_encryption_roundtrip(self):
        """Test email encryption with validation"""
        email = "test@example.com"
        encrypted = pii_encryption.encrypt_email(email)
        decrypted = pii_encryption.decrypt_email(encrypted)
        
        self.assertNotEqual(email, encrypted)
        self.assertEqual(email, decrypted)
    
    def test_invalid_email_encryption(self):
        """Test that invalid emails raise errors"""
        with self.assertRaises(EncryptionError):
            pii_encryption.encrypt_email("invalid-email")
    
    def test_none_values(self):
        """Test that None values are handled properly"""
        self.assertIsNone(pii_encryption.encrypt_string(None))
        self.assertIsNone(pii_encryption.decrypt_string(None))
        self.assertIsNone(pii_encryption.encrypt_email(None))
        self.assertIsNone(pii_encryption.decrypt_email(None))


# =============================================================================
# 2. SERIALIZER TESTS - Test encryption at serializer level
# =============================================================================

class UserSerializerTest(TestCase):
    """Test serializers handle encryption/decryption properly"""
    
    def setUp(self):
        """Create test user with encrypted data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-05-15',
            'bio': 'Test biography',
            'password': 'complexpass123!',
            'password_confirm': 'complexpass123!'
        }
    
    def test_user_registration_serializer_encryption(self):
        """Test that registration serializer encrypts data"""
        serializer = UserRegistrationSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        user = serializer.save()
        
        # Verify data is encrypted in database
        user.refresh_from_db()
        self.assertNotEqual(user.email, 'test@example.com')
        self.assertNotEqual(user.first_name, 'John')
        self.assertNotEqual(user.last_name, 'Doe')
        
        # Verify profile data is encrypted
        profile = user.profile
        self.assertNotEqual(profile.bio, 'Test biography')
        
        # Verify we can decrypt the data
        decrypted_email = pii_encryption.decrypt_email(user.email)
        self.assertEqual(decrypted_email, 'test@example.com')
    
    def test_user_serializer_decryption(self):
        """Test that UserSerializer decrypts data for API responses"""
        # First create encrypted user
        reg_serializer = UserRegistrationSerializer(data=self.user_data)
        self.assertTrue(reg_serializer.is_valid())
        user = reg_serializer.save()
        
        # Test UserSerializer returns decrypted data
        user_serializer = UserSerializer(user)
        data = user_serializer.data
        
        # Verify decrypted data is returned
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['date_of_birth'], '1990-05-15')
        self.assertEqual(data['bio'], 'Test biography')
    
    def test_duplicate_email_validation(self):
        """Test that duplicate email detection works with encryption"""
        # Create first user
        serializer1 = UserRegistrationSerializer(data=self.user_data)
        self.assertTrue(serializer1.is_valid())
        serializer1.save()
        
        # Try to create second user with same email
        user_data2 = self.user_data.copy()
        user_data2['username'] = 'testuser2'
        
        serializer2 = UserRegistrationSerializer(data=user_data2)
        self.assertFalse(serializer2.is_valid())
        self.assertIn('email', serializer2.errors)


# =============================================================================
# 3. API ENDPOINT TESTS - Test full API functionality
# =============================================================================

class UserAPITest(APITestCase):
    """Test API endpoints with encryption"""
    
    def setUp(self):
        self.client = APIClient()
        self.registration_data = {
            'username': 'apitest',
            'email': 'api@test.com',
            'first_name': 'API',
            'last_name': 'User',
            'date_of_birth': '1985-12-25',
            'bio': 'API test biography',
            'password': 'complexpass123!',
            'password_confirm': 'complexpass123!'
        }
    
    def test_user_registration_api(self):
        """Test user registration via API"""
        response = self.client.post('/api/register/', self.registration_data)
        
        # Verify successful registration
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify user was created with encrypted data
        user = User.objects.get(username='apitest')
        self.assertNotEqual(user.email, 'api@test.com')  # Should be encrypted
        self.assertNotEqual(user.first_name, 'API')     # Should be encrypted
    
    def test_get_user_profile_api(self):
        """Test getting user profile returns decrypted data"""
        # First register user
        reg_response = self.client.post('/api/register/', self.registration_data)
        access_token = reg_response.data['access']
        
        # Get profile with authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.get('/api/profile/')
        
        # Verify decrypted data is returned
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        data = profile_response.data
        
        self.assertEqual(data['email'], 'api@test.com')
        self.assertEqual(data['first_name'], 'API')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['date_of_birth'], '1985-12-25')
        self.assertEqual(data['bio'], 'API test biography')
    
    def test_update_user_profile_api(self):
        """Test updating profile encrypts new data"""
        # Register and get token
        reg_response = self.client.post('/api/register/', self.registration_data)
        access_token = reg_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Update profile
        update_data = {
            'first_name': 'Updated Name',
            'bio': 'Updated biography'
        }
        update_response = self.client.patch('/api/profile/update/', update_data)
        
        # Verify update succeeded
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Verify returned data is decrypted
        user_data = update_response.data['user']
        self.assertEqual(user_data['first_name'], 'Updated Name')
        self.assertEqual(user_data['bio'], 'Updated biography')
        
        # Verify data is encrypted in database
        user = User.objects.get(username='apitest')
        self.assertNotEqual(user.first_name, 'Updated Name')
    
    def test_list_users_api(self):
        """Test that user list returns decrypted public data"""
        # Register user
        reg_response = self.client.post('/api/register/', self.registration_data)
        access_token = reg_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Get users list
        list_response = self.client.get('/api/users/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        # Find our user in the list
        users = list_response.data
        api_user = next((u for u in users if u['username'] == 'apitest'), None)
        
        self.assertIsNotNone(api_user)
        self.assertEqual(api_user['first_name'], 'API')
        self.assertEqual(api_user['bio'], 'API test biography')
        # Email should not be in public list
        self.assertNotIn('email', api_user)


# =============================================================================
# 4. MANUAL TESTING SCRIPT - For interactive testing
# =============================================================================

def manual_test_encryption():
    """
    Manual testing script you can run in Django shell
    
    Run this with: python manage.py shell
    Then: exec(open('path/to/this/file.py').read()); manual_test_encryption()
    """
    print("=" * 50)
    print("MANUAL PII ENCRYPTION TEST")
    print("=" * 50)
    
    # Test 1: Basic encryption
    print("\n1. Testing basic encryption...")
    from api.utils.encryption import pii_encryption
    
    test_email = "manual@test.com"
    encrypted = pii_encryption.encrypt_email(test_email)
    decrypted = pii_encryption.decrypt_email(encrypted)
    
    print(f"Original email: {test_email}")
    print(f"Encrypted: {encrypted[:50]}...")
    print(f"Decrypted: {decrypted}")
    print(f"Round-trip successful: {test_email == decrypted}")
    
    # Test 2: User registration
    print("\n2. Testing user registration...")
    from api.serializers.auth_serializer import UserRegistrationSerializer
    
    user_data = {
        'username': f'manual_test_{id(manual_test_encryption)}',
        'email': 'manual@encryption.test',
        'first_name': 'Manual',
        'last_name': 'Test',
        'date_of_birth': '1990-01-01',
        'bio': 'Manual test biography',
        'password': 'complexpass123!',
        'password_confirm': 'complexpass123!'
    }
    
    serializer = UserRegistrationSerializer(data=user_data)
    if serializer.is_valid():
        user = serializer.save()
        print(f"User created: {user.username}")
        print(f"Email in DB (encrypted): {user.email[:50]}...")
        print(f"First name in DB (encrypted): {user.first_name[:30]}...")
        
        # Test 3: Profile retrieval
        print("\n3. Testing profile retrieval...")
        from api.serializers.auth_serializer import UserSerializer
        user_serializer = UserSerializer(user)
        
        print(f"API response email: {user_serializer.data['email']}")
        print(f"API response first_name: {user_serializer.data['first_name']}")
        print(f"API response bio: {user_serializer.data['bio']}")
        
        print("\n✅ Manual test completed successfully!")
    else:
        print(f"❌ Serializer errors: {serializer.errors}")


if __name__ == "__main__":
    # Instructions for running tests
    print("""
    PII ENCRYPTION TESTING GUIDE
    ============================
    
    1. Run unit tests:
       python manage.py test api.tests.test_pii_encryption
       
    2. Run specific test class:
       python manage.py test api.tests.test_pii_encryption.EncryptionUtilsTest
       
    3. Run with verbose output:
       python manage.py test api.tests.test_pii_encryption --verbosity=2
       
    4. Manual testing in Django shell:
       python manage.py shell
       >>> exec(open('this_file_path.py').read())
       >>> manual_test_encryption()
       
    5. API testing with curl:
       # Register user
       curl -X POST http://localhost:8000/api/register/ \\
         -H "Content-Type: application/json" \\
         -d '{"username":"curltest","email":"curl@test.com","first_name":"Curl","last_name":"Test","password":"complexpass123!","password_confirm":"complexpass123!"}'
       
       # Get profile (need token from registration)
       curl -X GET http://localhost:8000/api/profile/ \\
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """)