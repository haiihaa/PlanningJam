# Framework-generated: 0%
# Human-written: 100%
# AI-generated: 0%

from rest_framework import serializers
from ..utils.encryption import pii_encryption, EncryptionError

class LocationSerializer(serializers.Serializer):
    """Location serializer with encryption for address fields"""
    name = serializers.CharField(required=False)
    address1 = serializers.CharField()
    address2 = serializers.CharField(required=False)
    city = serializers.CharField()
    state = serializers.CharField()
    zipcode = serializers.CharField()  # Changed to CharField to store encrypted data
    
    def to_internal_value(self, data):
        """Encrypt address fields before processing"""
        if isinstance(data, dict):
            # Create a copy to avoid modifying the original data
            encrypted_data = data.copy()
            
            # Encrypt address fields
            try:
                if 'name' in encrypted_data and encrypted_data['name']:
                    encrypted_data['name'] = pii_encryption.encrypt_string(encrypted_data['name'])
                    
                if 'address1' in encrypted_data and encrypted_data['address1']:
                    encrypted_data['address1'] = pii_encryption.encrypt_string(encrypted_data['address1'])
                    
                if 'address2' in encrypted_data and encrypted_data['address2']:
                    encrypted_data['address2'] = pii_encryption.encrypt_string(encrypted_data['address2'])
                    
                if 'city' in encrypted_data and encrypted_data['city']:
                    encrypted_data['city'] = pii_encryption.encrypt_string(encrypted_data['city'])
                    
                if 'state' in encrypted_data and encrypted_data['state']:
                    encrypted_data['state'] = pii_encryption.encrypt_string(encrypted_data['state'])
                    
                if 'zipcode' in encrypted_data and encrypted_data['zipcode']:
                    encrypted_data['zipcode'] = pii_encryption.encrypt_int(encrypted_data['zipcode'])
                    
            except EncryptionError as e:
                raise serializers.ValidationError(f"Failed to encrypt location data: {str(e)}")
                
            return super().to_internal_value(encrypted_data)
        
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """Decrypt address fields for API responses"""
        if isinstance(instance, dict):
            # Create a copy to avoid modifying the original data
            decrypted_data = instance.copy()
            
            # Decrypt address fields
            try:
                if 'name' in decrypted_data and decrypted_data['name']:
                    try:
                        decrypted_data['name'] = pii_encryption.decrypt_string(decrypted_data['name'])
                    except EncryptionError:
                        # Keep original value if decryption fails (might be plain text)
                        pass
                        
                if 'address1' in decrypted_data and decrypted_data['address1']:
                    try:
                        decrypted_data['address1'] = pii_encryption.decrypt_string(decrypted_data['address1'])
                    except EncryptionError:
                        pass
                        
                if 'address2' in decrypted_data and decrypted_data['address2']:
                    try:
                        decrypted_data['address2'] = pii_encryption.decrypt_string(decrypted_data['address2'])
                    except EncryptionError:
                        pass
                        
                if 'city' in decrypted_data and decrypted_data['city']:
                    try:
                        decrypted_data['city'] = pii_encryption.decrypt_string(decrypted_data['city'])
                    except EncryptionError:
                        pass
                        
                if 'state' in decrypted_data and decrypted_data['state']:
                    try:
                        decrypted_data['state'] = pii_encryption.decrypt_string(decrypted_data['state'])
                    except EncryptionError:
                        pass
                        
                if 'zipcode' in decrypted_data and decrypted_data['zipcode']:
                    try:
                        decrypted_data['zipcode'] = pii_encryption.decrypt_int(decrypted_data['zipcode'])
                    except EncryptionError:
                        pass
                        
            except Exception as e:
                # Log error but don't fail the response
                pass
                
            return super().to_representation(decrypted_data)
        
        return super().to_representation(instance)

class PlansSerializer(serializers.Serializer):
    """Plans serializer with encrypted location data support"""
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False)
    location = LocationSerializer()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    created_by = serializers.CharField()
    created_at = serializers.DateTimeField()
    
    def validate(self, data):
        """Validate plan data including time constraints"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": "End time must be after start time."
            })
        return data