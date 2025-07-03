from cryptography.fernet import Fernet
import os
import base64
from typing import Optional

class EncryptionService:
    def __init__(self):
        # In production, this should be stored securely (e.g., environment variable)
        self.encryption_key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate a new one."""
        key_str = os.getenv("ENCRYPTION_KEY")
        if key_str:
            return base64.urlsafe_b64decode(key_str.encode())
        else:
            # Generate a new key (in production, save this securely)
            key = Fernet.generate_key()
            print(f"Generated new encryption key: {base64.urlsafe_b64encode(key).decode()}")
            print("Please save this key in your .env file as ENCRYPTION_KEY")
            return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64 encoded result."""
        if not data:
            return ""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Decrypt base64 encoded encrypted data."""
        if not encrypted_data:
            return None
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

# Singleton instance
encryption_service = EncryptionService()
