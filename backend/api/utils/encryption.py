"""
Encryption utilities for protecting sensitive PII data in PlanningJam

Provides field-level encryption for user personal information including:
- Email addresses
- Date of birth
- Personal biographies

Uses Fernet symmetric encryption with key derivation from Django SECRET_KEY
"""
import base64
import os
from datetime import date, datetime
from typing import Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors"""
    pass


class PIIEncryption:
    """
    Handles encryption and decryption of PII data using Fernet symmetric encryption
    
    Uses Django's SECRET_KEY as the base for key derivation to ensure
    consistency across application restarts.
    """
    
    def __init__(self):
        """Initialize encryption with key derived from Django SECRET_KEY"""
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """
        Initialize Fernet encryption using PBKDF2 key derivation
        
        Derives encryption key from Django SECRET_KEY to ensure consistency
        """
        try:
            # Use a fixed salt for consistency (in production, consider storing this separately)
            salt = b'planningjam_pii_salt_2025'
            
            # Derive key from Django SECRET_KEY
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
            self._fernet = Fernet(key)
            
        except Exception as e:
            raise EncryptionError(f"Failed to initialize encryption: {str(e)}")
    
    def encrypt_string(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt a string value
        
        Args:
            plaintext: String to encrypt (None/empty strings return as-is)
            
        Returns:
            Base64-encoded encrypted string or None
        """
        if not plaintext:
            return plaintext
            
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_string(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Decrypt a string value
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string or None
        """
        if not ciphertext:
            return ciphertext
            
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")
    
    def encrypt_email(self, email: Optional[str]) -> Optional[str]:
        """
        Encrypt email address with additional validation
        
        Args:
            email: Email address to encrypt
            
        Returns:
            Encrypted email or None
        """
        if not email:
            return email
            
        # Basic email format validation before encryption
        if '@' not in email or '.' not in email.split('@')[1]:
            raise EncryptionError("Invalid email format")
            
        return self.encrypt_string(email.lower().strip())
    
    def decrypt_email(self, encrypted_email: Optional[str]) -> Optional[str]:
        """
        Decrypt email address
        
        Args:
            encrypted_email: Encrypted email string
            
        Returns:
            Decrypted email address
        """
        return self.decrypt_string(encrypted_email)
    
    def encrypt_date(self, date_obj: Optional[Union[date, str]]) -> Optional[str]:
        """
        Encrypt date of birth
        
        Args:
            date_obj: Date object or ISO format string
            
        Returns:
            Encrypted date string
        """
        if not date_obj:
            return None
            
        # Convert date object to string if needed
        if isinstance(date_obj, date):
            date_str = date_obj.isoformat()
        else:
            date_str = str(date_obj)
            
        return self.encrypt_string(date_str)
    
    def decrypt_date(self, encrypted_date: Optional[str]) -> Optional[date]:
        """
        Decrypt date of birth
        
        Args:
            encrypted_date: Encrypted date string
            
        Returns:
            Date object or None
        """
        if not encrypted_date:
            return None
            
        date_str = self.decrypt_string(encrypted_date)
        if not date_str:
            return None
            
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError as e:
            raise EncryptionError(f"Invalid date format: {str(e)}")
    
    def encrypt_bio(self, bio: Optional[str]) -> Optional[str]:
        """
        Encrypt personal biography with length validation
        
        Args:
            bio: Biography text to encrypt
            
        Returns:
            Encrypted biography or None
        """
        if not bio:
            return bio
            
        # Validate biography length before encryption
        if len(bio) > 500:
            raise EncryptionError("Biography exceeds maximum length of 500 characters")
            
        return self.encrypt_string(bio.strip())
    
    def decrypt_bio(self, encrypted_bio: Optional[str]) -> Optional[str]:
        """
        Decrypt personal biography
        
        Args:
            encrypted_bio: Encrypted biography string
            
        Returns:
            Decrypted biography text
        """
        return self.decrypt_string(encrypted_bio)
    
    def encrypt_int(self, number: Optional[Union[int, str]]) -> Optional[str]:
        """
        Encrypt integer value (e.g., zipcode, phone numbers)
        
        Args:
            number: Integer or string representation of number to encrypt
            
        Returns:
            Encrypted number as string or None
        """
        if number is None:
            return None
            
        # Convert to string and validate it's a valid integer
        try:
            if isinstance(number, str):
                # Validate it's a valid integer string
                int(number)
                number_str = number.strip()
            else:
                number_str = str(number)
        except (ValueError, TypeError):
            raise EncryptionError(f"Invalid integer value: {number}")
            
        return self.encrypt_string(number_str)
    
    def decrypt_int(self, encrypted_number: Optional[str]) -> Optional[int]:
        """
        Decrypt integer value
        
        Args:
            encrypted_number: Encrypted number string
            
        Returns:
            Decrypted integer or None
        """
        if not encrypted_number:
            return None
            
        decrypted_str = self.decrypt_string(encrypted_number)
        if not decrypted_str:
            return None
            
        try:
            return int(decrypted_str)
        except ValueError as e:
            raise EncryptionError(f"Decrypted value is not a valid integer: {str(e)}")


# Global instance for application use
pii_encryption = PIIEncryption()