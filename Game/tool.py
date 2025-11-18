# tool.py

import secrets
import base64
import json # For RSA key output
import os # For RSA key saving
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad # Only needed for encryption
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP # Only needed for encryption
# We won't include the decryption functions as this script is for *creating* challenge data.

# --- Encryption Functions (Copied/Adapted from app/utils.py) ---

# AES Encryption
def generate_aes_key():
    """Generate a random AES key"""
    return get_random_bytes(16)  # 128 bits key

def generate_aes_iv():
    """Generate a random initialization vector for AES"""
    return get_random_bytes(16)

def aes_encrypt(plaintext, key=None, iv=None):
    """Encrypt plaintext using AES-CBC mode"""
    if key is None:
        key = generate_aes_key()
    if iv is None:
        iv = generate_aes_iv()

    # Convert plaintext to bytes if it's a string
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')

    # Pad the plaintext to be a multiple of AES block size (16 bytes)
    padded_plaintext = pad(plaintext, AES.block_size)

    # Create AES cipher and encrypt
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded_plaintext)

    # Return ciphertext, key, and iv (all base64 encoded for admin UI)
    return {
        'ciphertext_b64': base64.b64encode(ciphertext).decode('utf-8'),
        'key_b64': base64.b64encode(key).decode('utf-8'),
        'iv_b64': base64.b64encode(iv).decode('utf-8')
    }

# Vigenère Cipher
def vigenere_encrypt(plaintext, key=None):
    """Encrypt plaintext using Vigenère cipher"""
    if key is None:
        # Generate a random letter key if none provided
        letters = 'abcdefghijklmnopqrstuvwxyz'
        key = ''.join(secrets.choice(letters) for _ in range(8)) # 8 random letters

    if isinstance(key, bytes):
        key = key.decode('utf-8')
    if isinstance(plaintext, bytes):
        plaintext = plaintext.decode('utf-8')

    # Ensure key is only letters and uppercase for encryption logic
    key = ''.join(c for c in key if c.isalpha()).upper()
    if not key:
        print("Warning: Provided Vigenere key has no letters. Using a default for encryption.")
        key = "DEFAULTKEY"

    ciphertext = ""
    key_index = 0

    for char in plaintext:
        # Only encrypt letters
        if char.isalpha():
            shift = ord(key[key_index % len(key)]) - ord('A')
            if char.isupper():
                char_code = ord(char) - ord('A')
                encrypted_char = chr((char_code + shift) % 26 + ord('A'))
            else: # islower
                char_code = ord(char) - ord('a')
                encrypted_char = chr((char_code + shift) % 26 + ord('a')) # Keep original case
            key_index += 1 # Move to the next key char only for letters
            ciphertext += encrypted_char
        else:
            # Non-alphabetic characters pass through unchanged
            ciphertext += char

    return {
        'ciphertext': ciphertext,
        'key': key, # Return the clean key used
        'iv': None
    }

# RSA Encryption
def generate_rsa_key_pair(key_size=2048):
    """Generate an RSA key pair"""
    key = RSA.generate(key_size)
    private_key = key.export_key().decode('utf-8')
    public_key = key.publickey().export_key().decode('utf-8')
    return {
        'private_key': private_key,
        'public_key': public_key
    }

def rsa_encrypt(plaintext, public_key_str):
    """Encrypt plaintext using RSA public key"""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')

    try:
        # Import the public key
        public_key = RSA.import_key(public_key_str)

        # Create PKCS#1 OAEP cipher and encrypt
        cipher = PKCS1_OAEP.new(public_key)

        # RSA can only encrypt data up to a certain size (key_size / 8 - padding)
        # For 2048 bits (256 bytes), padding is 42 bytes, so max size is 256 - 42 = 214 bytes
        max_size = public_key.size_in_bytes() - 42 # OAEP padding size

        if len(plaintext) > max_size:
            print(f"Warning: Plaintext is too large for RSA ({len(plaintext)} bytes > {max_size} bytes). Truncating...")
            plaintext = plaintext[:max_size] # Truncate to fit

        ciphertext = cipher.encrypt(plaintext)

        # Return ciphertext (base64 encoded) and the public key used
        return {
            'ciphertext_b64': base64.b64encode(ciphertext).decode('utf-8'),
            'public_key_str': public_key_str, # The key used for encryption
            'iv': None
        }
    except Exception as e:
         print(f"RSA Encryption Error: {e}")
         return None # Indicate failure


# --- Main Script Logic ---

def run_encryption_script():
    print("--- CTF Challenge Data Generator (Encryption) ---")

    plaintext = input("Enter the plaintext/flag (e.g., HelloWorld): ")
    if not plaintext:
        print("Plaintext cannot be empty.")
        return

    print("\nChoose encryption type:")
    print("1. AES (requires key & IV)")
    print("2. Vigenère (requires key)")
    print("3. RSA (generates key pair, encrypts with public key)")

    while True:
        choice = input("Enter choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    encryption_result = None
    crypto_key_info = None # For AES/Vigenere keys, RSA key pair

    if choice == '1': # AES
        print("\n--- AES Encryption ---")
        # Admin provides key/IV, or generate
        generate_new = input("Generate new AES key and IV? (y/n, default y): ").strip().lower() or 'y'
        if generate_new == 'y':
            aes_key = generate_aes_key()
            aes_iv = generate_aes_iv()
            print("Generated new AES Key and IV.")
        else:
            key_input_b64 = input("Enter AES Key (base64): ").strip()
            iv_input_b64 = input("Enter AES IV (base64): ").strip()
            try:
                aes_key = base64.b64decode(key_input_b64)
                aes_iv = base64.b64decode(iv_input_b64)
                if len(aes_key) != 16 or len(aes_iv) != 16:
                    print("Warning: Key or IV size is incorrect (should be 16 bytes).")
            except:
                print("Invalid base64 input for key or IV.")
                return

        encryption_result = aes_encrypt(plaintext, key=aes_key, iv=aes_iv)
        if encryption_result:
             crypto_key_info = {
                'key_b64': encryption_result['key_b64'],
                'iv_b64': encryption_result['iv_b64']
             }
             del encryption_result['key_b64'] # Remove keys from main result to avoid confusion
             del encryption_result['iv_b64']


    elif choice == '2': # Vigenère
        print("\n--- Vigenère Encryption ---")
        vigenere_key = input("Enter Vigenère Key (letters only recommended): ").strip()
        encryption_result = vigenere_encrypt(plaintext, key=vigenere_key)
        if encryption_result:
            crypto_key_info = {'key': encryption_result['key']}
            del encryption_result['key'] # Remove key from main result

    elif choice == '3': # RSA
        print("\n--- RSA Encryption ---")
        key_pair = generate_rsa_key_pair() # Generate a new key pair every time
        print("Generated new RSA Key Pair.")
        encryption_result = rsa_encrypt(plaintext, key_pair['public_key'])
        if encryption_result:
            # For RSA, the config JSON needs the PRIVATE key for verification (decrypting)
            # and the PUBLIC key might be needed for the challenge data description.
             crypto_key_info = {
                'public_key': key_pair['public_key'],
                'private_key': key_pair['private_key']
             }
             del encryption_result['public_key_str'] # Remove public key from main result


    # --- Output Results ---
    print("\n--- Results ---")
    if encryption_result:
        print("Plaintext:", plaintext)
        print("Encryption Type:", ['AES', 'Vigenère', 'RSA'][int(choice)-1])

        # Output the ciphertext/challenge_data
        if 'ciphertext_b64' in encryption_result:
            print("Ciphertext (Base64):", encryption_result['ciphertext_b64'])
            challenge_data_output = encryption_result['ciphertext_b64']
        elif 'ciphertext' in encryption_result: # Vigenere raw string
            print("Ciphertext:", encryption_result['ciphertext'])
            challenge_data_output = encryption_result['ciphertext']
        else:
            challenge_data_output = "" # Should not happen if encryption was successful


        print("\n--> Admin Challenge Creation Form Values:")
        print(f"Category: Cryptography") # This script is only for Crypto
        print(f"Difficulty: (Choose manually in form)")
        print(f"Title: (Choose manually in form)")
        print(f"Description: (Describe the challenge, maybe mention encryption type)")
        print(f"Flag (Solution): {plaintext}") # The original plaintext is the flag content
        print(f"Challenge Data/Instructions: {challenge_data_output}") # This is the output ciphertext/data

        if choice == '1': # AES
             print(f"Encryption Type: aes")
             config_json_output = json.dumps({
                'key': crypto_key_info['key_b64'],
                'iv': crypto_key_info['iv_b64']
             })
             print(f"Configuration (JSON or Text): {config_json_output}")

        elif choice == '2': # Vigenere
             print(f"Encryption Type: vigenere")
             config_json_output = json.dumps({
                'key': crypto_key_info['key']
             })
             print(f"Configuration (JSON or Text): {config_json_output}")

        elif choice == '3': # RSA
             print(f"Encryption Type: rsa")
             # Config JSON needs the PRIVATE key for verification
             config_json_output = json.dumps({
                 'private_key': crypto_key_info['private_key']
             })
             print(f"Configuration (JSON or Text): {config_json_output}")
             print("\n--> RSA Key Pair (SAVE THIS PRIVATE KEY):")
             print("Public Key:\n", crypto_key_info['public_key'])
             print("-" * 20)
             print("Private Key:\n", crypto_key_info['private_key'])
             print("-" * 20)

             # Optional: Offer to save keys to files
             save_keys = input("Save RSA keys to files? (y/n, default n): ").strip().lower() or 'n'
             if save_keys == 'y':
                 try:
                     with open("rsa_public_key.pem", "w") as f:
                         f.write(crypto_key_info['public_key'])
                     with open("rsa_private_key.pem", "w") as f:
                         f.write(crypto_key_info['private_key'])
                     print("RSA keys saved to rsa_public_key.pem and rsa_private_key.pem")
                 except Exception as e:
                     print(f"Error saving keys: {e}")


    else:
        print("Encryption failed.")

# Run the script if executed directly
if __name__ == "__main__":
    run_encryption_script()
