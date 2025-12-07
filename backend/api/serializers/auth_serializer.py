from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from ..models import UserProfile
from ..utils.encryption import pii_encryption, EncryptionError

# Framework-generated: 5%
# Human-written: 45%
# AI-generated: 50%
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'date_of_birth', 'bio', 'password', 'password_confirm')
    
    def validate_email(self, value):
        """
        Validate that the email is unique, checking against encrypted emails in database.
        """
        # Check for existing users by comparing with encrypted emails
        existing_users = User.objects.all()
        
        for user in existing_users:
            if user.email:
                try:
                    # Try to decrypt and compare
                    decrypted_email = pii_encryption.decrypt_email(user.email)
                    if decrypted_email and decrypted_email.lower() == value.lower():
                        raise serializers.ValidationError("A user with this email already exists.")
                except EncryptionError:
                    # If decryption fails, might be plain text (during migration)
                    if user.email.lower() == value.lower():
                        raise serializers.ValidationError("A user with this email already exists.")
        
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        # Extract profile data
        profile_data = {
            'date_of_birth': validated_data.pop('date_of_birth', None),
            'bio': validated_data.pop('bio', '')
        }
        
        # Encrypt email before creating user
        if validated_data.get('email'):
            try:
                validated_data['email'] = pii_encryption.encrypt_email(validated_data['email'])
            except EncryptionError as e:
                raise serializers.ValidationError({"email": f"Failed to encrypt email: {str(e)}"})
        
        # Encrypt first and last names
        if validated_data.get('first_name'):
            try:
                validated_data['first_name'] = pii_encryption.encrypt_string(validated_data['first_name'])
            except EncryptionError as e:
                raise serializers.ValidationError({"first_name": f"Failed to encrypt first name: {str(e)}"})
                
        if validated_data.get('last_name'):
            try:
                validated_data['last_name'] = pii_encryption.encrypt_string(validated_data['last_name'])
            except EncryptionError as e:
                raise serializers.ValidationError({"last_name": f"Failed to encrypt last name: {str(e)}"})
        
        # Create user
        validated_data.pop('password_confirm')
        validated_data['password'] = make_password(validated_data['password'])
        user = User.objects.create(**validated_data)
        
        # Encrypt and create user profile
        try:
            if profile_data['bio']:
                profile_data['bio'] = pii_encryption.encrypt_string(profile_data['bio'])
        except EncryptionError as e:
            # Clean up created user if profile encryption fails
            user.delete()
            raise serializers.ValidationError({"profile": f"Failed to encrypt profile data: {str(e)}"})
        
        UserProfile.objects.create(user=user, **profile_data)
        
        return user

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with automatic PII decryption for API responses"""
    id = serializers.CharField(read_only=True)
    date_of_birth = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_of_birth', 'bio', 'date_joined')
        read_only_fields = ('id', 'date_joined')
    
    def get_email(self, obj):
        """Decrypt email for API response"""
        if not obj.email:
            return None
        try:
            return pii_encryption.decrypt_email(obj.email)
        except EncryptionError:
            # Fallback for plain text during migration
            return obj.email if '@' in str(obj.email) else None
    
    def get_first_name(self, obj):
        """Decrypt first name for API response"""
        if not obj.first_name:
            return ''
        try:
            return pii_encryption.decrypt_string(obj.first_name)
        except EncryptionError:
            return obj.first_name
    
    def get_last_name(self, obj):
        """Decrypt last name for API response"""
        if not obj.last_name:
            return ''
        try:
            return pii_encryption.decrypt_string(obj.last_name)
        except EncryptionError:
            return obj.last_name
    
    def get_date_of_birth(self, obj):
        """Decrypt date of birth from profile"""
        if not hasattr(obj, 'profile') or not obj.profile.date_of_birth:
            return None
        return obj.profile.date_of_birth.isoformat()
    
    def get_bio(self, obj):
        """Decrypt bio from profile"""
        if not hasattr(obj, 'profile') or not obj.profile.bio:
            return ''
        try:
            return pii_encryption.decrypt_string(obj.profile.bio)
        except EncryptionError:
            return obj.profile.bio


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile fields with automatic encryption
    """
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'date_of_birth', 'bio')
    
    def update(self, instance, validated_data):
        # Extract profile-specific data
        profile_data = {
            'date_of_birth': validated_data.pop('date_of_birth', None),
            'bio': validated_data.pop('bio', None)
        }
        
        # Encrypt user fields before updating
        if 'first_name' in validated_data and validated_data['first_name']:
            try:
                validated_data['first_name'] = pii_encryption.encrypt_string(validated_data['first_name'])
            except EncryptionError as e:
                raise serializers.ValidationError({"first_name": f"Failed to encrypt first name: {str(e)}"})
        
        if 'last_name' in validated_data and validated_data['last_name']:
            try:
                validated_data['last_name'] = pii_encryption.encrypt_string(validated_data['last_name'])
            except EncryptionError as e:
                raise serializers.ValidationError({"last_name": f"Failed to encrypt last name: {str(e)}"})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create profile with encryption
        profile, created = UserProfile.objects.get_or_create(user=instance)
        
        try:            
            if profile_data['bio'] is not None:
                if profile_data['bio']:
                    profile.bio = pii_encryption.encrypt_string(profile_data['bio'])
                else:
                    profile.bio = ''
            
            profile.save()
            
        except EncryptionError as e:
            raise serializers.ValidationError({"profile": f"Failed to encrypt profile data: {str(e)}"})
        
        return instance