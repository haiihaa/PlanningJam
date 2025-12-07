"""
Test suite for plan location encryption functionality
"""
import pytest
from unittest.mock import patch
from rest_framework import serializers
from rest_framework.test import APITestCase

from api.serializers.plans_serializer import LocationSerializer, PlansSerializer
from api.utils.encryption import pii_encryption, EncryptionError


class TestLocationSerializerEncryption(APITestCase):
    """Test encryption/decryption in LocationSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_location = {
            'name': 'Central Park Pavilion',
            'address1': '123 Main Street',
            'address2': 'Suite 456',
            'city': 'New York',
            'state': 'NY',
            'zipcode': '10001'
        }
    
    def test_location_encryption_success(self):
        """Test successful encryption of all location fields"""
        serializer = LocationSerializer(data=self.sample_location)
        
        # Should validate successfully
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Check that data was encrypted (shouldn't match original)
        validated_data = serializer.validated_data
        self.assertNotEqual(validated_data['name'], self.sample_location['name'])
        self.assertNotEqual(validated_data['address1'], self.sample_location['address1'])
        self.assertNotEqual(validated_data['address2'], self.sample_location['address2'])
        self.assertNotEqual(validated_data['city'], self.sample_location['city'])
        self.assertNotEqual(validated_data['state'], self.sample_location['state'])
        self.assertNotEqual(validated_data['zipcode'], self.sample_location['zipcode'])
    
    def test_location_decryption_success(self):
        """Test successful decryption of location fields"""
        # First encrypt the data
        serializer = LocationSerializer(data=self.sample_location)
        self.assertTrue(serializer.is_valid())
        encrypted_data = serializer.validated_data
        
        # Then test decryption through to_representation
        decrypted_data = serializer.to_representation(encrypted_data)
        
        # Should match original data
        self.assertEqual(decrypted_data['name'], self.sample_location['name'])
        self.assertEqual(decrypted_data['address1'], self.sample_location['address1'])
        self.assertEqual(decrypted_data['address2'], self.sample_location['address2'])
        self.assertEqual(decrypted_data['city'], self.sample_location['city'])
        self.assertEqual(decrypted_data['state'], self.sample_location['state'])
        self.assertEqual(int(decrypted_data['zipcode']), int(self.sample_location['zipcode']))
    
    def test_zipcode_integer_handling(self):
        """Test that zipcode handles both string and integer inputs"""
        # Test with integer zipcode
        location_with_int_zip = self.sample_location.copy()
        location_with_int_zip['zipcode'] = 10001
        
        serializer = LocationSerializer(data=location_with_int_zip)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        encrypted_data = serializer.validated_data
        decrypted_data = serializer.to_representation(encrypted_data)
        
        # Should return integer zipcode
        self.assertEqual(int(decrypted_data['zipcode']), 10001)
    
    def test_optional_fields_handling(self):
        """Test encryption with optional fields missing"""
        minimal_location = {
            'address1': '123 Main Street',
            'city': 'Boston',
            'state': 'MA',
            'zipcode': '02101'
        }
        
        serializer = LocationSerializer(data=minimal_location)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        encrypted_data = serializer.validated_data
        decrypted_data = serializer.to_representation(encrypted_data)
        
        # Required fields should be present and decrypted
        self.assertEqual(decrypted_data['address1'], '123 Main Street')
        self.assertEqual(decrypted_data['city'], 'Boston')
        self.assertEqual(decrypted_data['state'], 'MA')
        self.assertEqual(int(decrypted_data['zipcode']), 2101)

    
    def test_invalid_zipcode_handling(self):
        """Test error handling for invalid zipcode"""
        invalid_location = self.sample_location.copy()
        invalid_location['zipcode'] = 'invalid_zip'
        
        serializer = LocationSerializer(data=invalid_location)
        
        # Should fail validation due to encryption error
        self.assertFalse(serializer.is_valid())
        
    
    def test_decryption_error_graceful_handling(self):
        """Test that decryption errors don't break the response"""
        # Create data with invalid encrypted values
        invalid_encrypted_data = {
            'name': 'invalid_encrypted_data',
            'address1': 'also_invalid',
            'address2': '',
            'city': 'invalid_city_data',
            'state': 'bad_state',
            'zipcode': 'not_encrypted_properly'
        }
        
        serializer = LocationSerializer()
        
        # Should not raise exception, but return original values
        result = serializer.to_representation(invalid_encrypted_data)
        
        # Should return the invalid data as-is (graceful degradation)
        self.assertEqual(result['name'], 'invalid_encrypted_data')
        self.assertEqual(result['address1'], 'also_invalid')


class TestPlansSerializerWithLocationEncryption(APITestCase):
    """Test PlansSerializer integration with encrypted locations"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_plan = {
            'title': 'Annual Company Picnic',
            'description': 'Fun outdoor event for all employees',
            'location': {
                'name': 'Riverside Park',
                'address1': '789 River Road',
                'address2': 'Pavilion A',
                'city': 'Springfield',
                'state': 'IL',
                'zipcode': '62701'
            },
            'start_time': '2025-07-15T10:00:00Z',
            'end_time': '2025-07-15T16:00:00Z',
            'created_by': 'user123',
            'created_at': '2025-01-01T12:00:00Z'
        }
    
    def test_plan_with_encrypted_location_success(self):
        """Test successful plan creation with encrypted location"""
        serializer = PlansSerializer(data=self.sample_plan)
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Validate that location data was encrypted
        validated_data = serializer.validated_data
        location_data = validated_data['location']
        
        # Location fields should be encrypted (not matching original)
        self.assertNotEqual(location_data['name'], self.sample_plan['location']['name'])
        self.assertNotEqual(location_data['address1'], self.sample_plan['location']['address1'])
        self.assertNotEqual(location_data['city'], self.sample_plan['location']['city'])
    
    def test_plan_time_validation_with_encryption(self):
        """Test that time validation still works with encrypted location"""
        invalid_plan = self.sample_plan.copy()
        # Set end time before start time
        invalid_plan['end_time'] = '2025-07-15T08:00:00Z'
        
        serializer = PlansSerializer(data=invalid_plan)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('End time must be after start time', str(serializer.errors))
    
    def test_plan_serialization_response(self):
        """Test complete plan serialization with location decryption"""
        serializer = PlansSerializer(data=self.sample_plan)
        self.assertTrue(serializer.is_valid())
        
        # Simulate storage and retrieval
        stored_data = serializer.validated_data
        
        # Test representation (what API would return)
        response_data = PlansSerializer(stored_data).data
        
        # Location should be properly decrypted in response
        response_location = response_data['location']
        original_location = self.sample_plan['location']
        
        self.assertEqual(response_location['name'], original_location['name'])
        self.assertEqual(response_location['address1'], original_location['address1'])
        self.assertEqual(response_location['address2'], original_location['address2'])
        self.assertEqual(response_location['city'], original_location['city'])
        self.assertEqual(response_location['state'], original_location['state'])
        self.assertEqual(response_location['zipcode'], original_location['zipcode'])


class TestLocationEncryptionIntegration(APITestCase):
    """Integration tests for location encryption functionality"""
    
    def test_encryption_roundtrip_consistency(self):
        """Test that multiple encrypt/decrypt cycles maintain data integrity"""
        original_data = {
            'name': 'Test Location',
            'address1': '456 Oak Avenue',
            'address2': 'Building B',
            'city': 'Chicago',
            'state': 'IL',
            'zipcode': '60601'
        }
        
        # Perform multiple roundtrips
        for i in range(3):
            serializer = LocationSerializer(data=original_data)
            self.assertTrue(serializer.is_valid(), f"Iteration {i}: {serializer.errors}")
            
            encrypted_data = serializer.validated_data
            decrypted_data = serializer.to_representation(encrypted_data)
            
            # Data should remain consistent
            self.assertEqual(decrypted_data['name'], original_data['name'])
            self.assertEqual(decrypted_data['address1'], original_data['address1'])
            self.assertEqual(decrypted_data['address2'], original_data['address2'])
            self.assertEqual(decrypted_data['city'], original_data['city'])
            self.assertEqual(decrypted_data['state'], original_data['state'])
            self.assertEqual(int(decrypted_data['zipcode']), int(original_data['zipcode']))
    
    def test_special_characters_in_address(self):
        """Test encryption with special characters and unicode"""
        special_location = {
            'name': 'Café & Restaurant',
            'address1': '123 Müller Straße',
            'address2': 'Apt #4-B',
            'city': 'São Paulo',
            'state': 'SP',
            'zipcode': '01000'
        }
        
        serializer = LocationSerializer(data=special_location)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        encrypted_data = serializer.validated_data
        decrypted_data = serializer.to_representation(encrypted_data)
        
        # Special characters should be preserved
        self.assertEqual(decrypted_data['name'], 'Café & Restaurant')
        self.assertEqual(decrypted_data['address1'], '123 Müller Straße')
        self.assertEqual(decrypted_data['address2'], 'Apt #4-B')
        self.assertEqual(decrypted_data['city'], 'São Paulo')
    
    def test_performance_with_large_address_data(self):
        """Test encryption performance with large address strings"""
        large_location = {
            'name': 'A' * 100,  # Long location name
            'address1': 'Very Long Street Name With Many Words ' * 5,
            'address2': 'Extended Suite Information ' * 3,
            'city': 'LongCityNameExample',
            'state': 'CA',
            'zipcode': '90210'
        }
        
        serializer = LocationSerializer(data=large_location)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        encrypted_data = serializer.validated_data
        decrypted_data = serializer.to_representation(encrypted_data)
        
        # Large data should be handled correctly
        self.assertEqual(decrypted_data['name'], large_location['name'])
        self.assertEqual(decrypted_data['address1'], large_location['address1'])
        self.assertEqual(decrypted_data['address2'], large_location['address2'])


if __name__ == '__main__':
    pytest.main([__file__])