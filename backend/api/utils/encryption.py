"""
Encryption utilities for protecting sensitive PII data in PlanningJam

Provides field-level encryption for user personal information including:
- Email addresses
- Date of birth
- Personal biographies

Uses Fernet symmetric encryption with:
- PII_ENCRYPTION_KEY environment variable (preferred for production)
- Fallback to key derivation from Django SECRET_KEY (backward compatibility)

To generate a new PII_ENCRYPTION_KEY:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64
import logging
import os
from datetime import date, datetime
from typing import Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors"""
    pass


class PIIEncryption:
    """
    Handles encryption and decryption of PII data using Fernet symmetric encryption
    
    Key Priority:
    1. PII_ENCRYPTION_KEY environment variable (recommended for production)
    2. Derived from Django SECRET_KEY (fallback for backward compatibility)
    """
    
    KEY_SOURCE_EXPLICIT = "explicit"
    KEY_SOURCE_DERIVED = "derived"
    
    def __init__(self):
        """Initialize encryption with key from environment or derived from SECRET_KEY"""
        self._fernet = None
        self._key_source = None
        self._initialize_encryption()
    
    def _get_explicit_key(self) -> Optional[bytes]:
        """
        Get explicit encryption key from PII_ENCRYPTION_KEY environment variable
        
        Returns:
            bytes: The encryption key if valid, None otherwise
        """
        explicit_key = os.environ.get('PII_ENCRYPTION_KEY')
        
        if explicit_key:
            try:
                key_bytes = explicit_key.encode() if isinstance(explicit_key, str) else explicit_key
                # Validate the key by attempting to create a Fernet instance
                Fernet(key_bytes)
                return key_bytes
            except Exception:
                logger.warning(
                    "PII_ENCRYPTION_KEY is invalid. Falling back to SECRET_KEY derivation. "
                    "Generate a valid key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
                return None
        return None
    
    def _derive_key_from_secret(self) -> bytes:
        """
        Derive encryption key from Django SECRET_KEY using PBKDF2
        
        Returns:
            bytes: The derived encryption key
        """
        salt = b'planningjam_pii_salt_2025'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    
    def _initialize_encryption(self):
        """
        Initialize Fernet encryption preferring PII_ENCRYPTION_KEY if available,
        otherwise falling back to SECRET_KEY derivation for backward compatibility.
        """
        try:
            # Try explicit key first (preferred for production)
            explicit_key = self._get_explicit_key()
            
            if explicit_key:
                self._fernet = Fernet(explicit_key)
                self._key_source = self.KEY_SOURCE_EXPLICIT
                logger.info("PII encryption initialized with explicit PII_ENCRYPTION_KEY")
            else:
                # Fallback to derived key for backward compatibility
                derived_key = self._derive_key_from_secret()
                self._fernet = Fernet(derived_key)
                self._key_source = self.KEY_SOURCE_DERIVED
                logger.info("PII encryption initialized with key derived from SECRET_KEY")
                
        except Exception as e:
            raise EncryptionError(f"Failed to initialize encryption: {str(e)}")
    
    @property
    def key_source(self) -> str:
        """Return the source of the encryption key ('explicit' or 'derived')"""
        return self._key_source
    
    def is_using_explicit_key(self) -> bool:
        """Check if encryption is using an explicit PII_ENCRYPTION_KEY"""
        return self._key_source == self.KEY_SOURCE_EXPLICIT
    
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