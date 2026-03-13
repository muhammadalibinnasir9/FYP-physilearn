from cryptography.fernet import Fernet
from django.conf import settings
import base64

# In a production environment, this key should be stored in environment variables.
# For this demo, we'll generate one if not provided, but it's not persistent!
ENCRYPTION_KEY = getattr(settings, 'FIELD_ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_value(value):
    if value is None:
        return None
    return cipher_suite.encrypt(str(value).encode()).decode()

def decrypt_value(token):
    if token is None:
        return None
    try:
        return cipher_suite.decrypt(token.encode()).decode()
    except Exception:
        # If decryption fails (e.g. key changed), return None instead of crashing
        return None
