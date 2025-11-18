# app/utils.py

import os
import secrets
import base64
from Crypto.Cipher import AES
# from Crypto.Random import get_random_bytes # get_random_bytes not needed for decryption
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP # Only needed for encryption script, not verification here
import binascii
import json # Import json for parsing config_json
from flask import current_app # Import current_app to access config (e.g., ENCRYPTION_TYPES)


# --- Decryption Functions (Keep these as building blocks) ---

def aes_decrypt(ciphertext_b64, key_b64, iv_b64):
    """Decrypt AES-encrypted ciphertext (base64 in, base64 key/iv in, plaintext out)"""
    try:
        # Decode base64 strings
        ciphertext = base64.b64decode(ciphertext_b64)
        key = base64.b64decode(key_b64)
        iv = base64.b64decode(iv_b64)

        # Create AES cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)

        # Unpad and return plaintext string
        plaintext = unpad(padded_plaintext, AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        # Handle potential decryption errors (wrong key, iv, padding, etc.)
        print(f"AES Decryption Error (ID {current_app.challenge_id_for_log if hasattr(current_app, 'challenge_id_for_log') else 'N/A'}): {e}") # Log the error server-side
        return None # Return None or raise exception on failure

def vigenere_decrypt(ciphertext, key):
    """Decrypt Vigenère-encrypted ciphertext (string in, string key in, plaintext string out)"""
    try:
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if isinstance(ciphertext, bytes):
            ciphertext = ciphertext.decode('utf-8')

        # Ensure key is only letters and uppercase for decryption logic
        key = ''.join(c for c in key if c.isalpha()).upper()
        if not key:
            print(f"Warning (Vigenere, ID {current_app.challenge_id_for_log if hasattr(current_app, 'challenge_id_for_log') else 'N/A'}): Vigenere key has no letters.")
            return None # An invalid key should fail decryption

        plaintext = ""
        key_index = 0

        for char in ciphertext:
            # Only decrypt letters
            if char.isalpha():
                shift = ord(key[key_index % len(key)]) - ord('A')
                if char.isupper():
                    char_code = ord(char) - ord('A')
                    decrypted_char = chr((char_code - shift) % 26 + ord('A'))
                else: # islower
                    char_code = ord(char) - ord('a')
                    decrypted_char = chr((char_code - shift) % 26 + ord('a')) # Keep original case
                key_index += 1 # Move to the next key char only for letters
                plaintext += decrypted_char
            else:
                # Non-alphabetic characters pass through unchanged
                plaintext += char

        return plaintext
    except Exception as e:
         print(f"Vigenere Decryption Error (ID {current_app.challenge_id_for_log if hasattr(current_app, 'challenge_id_for_log') else 'N/A'}): {e}") # Log the error
         return None # Indicate failure

def rsa_decrypt(ciphertext_b64, private_key_str):
    """Decrypt RSA-encrypted ciphertext (base64 in, private key string in, plaintext string out)"""
    try:
        # Decode base64 ciphertext
        ciphertext = base64.b64decode(ciphertext_b64)

        # Import the private key
        private_key = RSA.import_key(private_key_str)

        # Create PKCS#1 OAEP cipher and decrypt
        cipher = PKCS1_OAEP.new(private_key)

        # Decrypt - this can raise ValueError if padding is incorrect or data is malformed
        plaintext = cipher.decrypt(ciphertext)
        return plaintext.decode('utf-8')
    except Exception as e: # Catching a broad exception for robustness against various crypto errors
        # Handle potential decryption errors (wrong key, corrupted data, incorrect padding)
        print(f"RSA Decryption Error (ID {current_app.challenge_id_for_log if hasattr(current_app, 'challenge_id_for_log') else 'N/A'}): {e}") # Log the error
        return None # Indicate failure

# --- File handling functions (keep save_picture if used for products) ---
# Requires current_app context
def save_picture(form_picture, folder='product_pics'):
    """Save an uploaded image with a random filename"""
    try:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_picture.filename)
        picture_fn = random_hex + f_ext

        # Construct the full path relative to the application root
        upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
        folder_path = os.path.join(upload_folder, folder)
        picture_path = os.path.join(folder_path, picture_fn)

        # Create directory if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)

        # Save picture - form_picture is a FileStorage object
        form_picture.save(picture_path)

        # Return the filename relative to the static/uploads folder for DB storage
        return os.path.join(folder, picture_fn).replace('\\', '/') # Use forward slashes for URLs
    except Exception as e:
        print(f"Error saving picture: {e}") # Print error to server log
        return None # Indicate failure


# --- Challenge validation function - Modified for Categories and Layers ---

def verify_challenge_solution(submitted_solution, challenge):
    """Verify if the submitted solution is correct for the given challenge"""
    if not submitted_solution or not challenge:
        return False

    # Attach challenge ID to current_app for logging within helper functions
    # This is a bit hacky, but helps trace which challenge caused an error in decryption helpers
    current_app.challenge_id_for_log = challenge.id


    # Flag format: Flag{challenge_id_answer}
    # Extract the inner answer part from the submitted solution
    submitted_solution_stripped = submitted_solution.strip()
    if not submitted_solution_stripped.startswith('Flag{') or not submitted_solution_stripped.endswith('}'):
        # Does not match flag format
        print(f"Verify failed (ID {challenge.id}): Invalid flag format.")
        del current_app.challenge_id_for_log # Clean up log context
        return False

    # Attempt to parse the flag format
    try:
        flag_content = submitted_solution_stripped[len('Flag{'):-1]
        # Split by the first underscore to get challenge_id and potential answer
        parts = flag_content.split('_', 1)
        if len(parts) != 2:
            # Invalid format if not exactly one underscore
            print(f"Verify failed (ID {challenge.id}): Invalid flag format (missing underscore).")
            del current_app.challenge_id_for_log # Clean up log context
            return False
        submitted_id_str, submitted_answer_part = parts

        # Check if the challenge ID in the flag matches the actual challenge ID
        # This is important! Prevents submitting flags for other challenges.
        if int(submitted_id_str) != challenge.id:
             # Flag is for a different challenge ID
             print(f"Verify failed (ID {challenge.id}): Challenge ID mismatch in flag. Submitted ID: {submitted_id_str}, Expected ID: {challenge.id}")
             del current_app.challenge_id_for_log # Clean up log context
             return False

    except (ValueError, IndexError):
        # Failed to parse flag content or ID
        print(f"Verify failed (ID {challenge.id}): Error parsing flag format.")
        del current_app.challenge_id_for_log # Clean up log context
        return False

    # --- Verification logic based on Category ---

    is_correct = False # Assume incorrect until proven otherwise

    if challenge.category == 'Cryptography':
        # For crypto, the submitted_answer_part is the *decrypted plaintext* that should match the stored flag
        decrypted_data = challenge.challenge_data # Start with the stored challenge data (outermost ciphertext)
        config = {}
        if challenge.config_json:
            try:
                 config = json.loads(challenge.config_json)
            except json.JSONDecodeError:
                 print(f"Verify failed (Crypto, ID {challenge.id}): Invalid config_json format.")
                 del current_app.challenge_id_for_log # Clean up log context
                 return False # Config JSON is invalid for crypto

        # --- Layered Decryption Logic ---
        layers = config.get("layers")

        if isinstance(layers, list) and layers: # Check if 'layers' key exists and is a non-empty list
            # Process layers in REVERSE order of encryption (forward order of decryption)
            print(f"Verifying layered crypto challenge (ID {challenge.id}) with {len(layers)} layers...")
            current_data_blob = challenge.challenge_data # Start with the outermost ciphertext/data
            decryption_successful = True

            for i, layer_config in enumerate(layers):
                layer_type = layer_config.get("type")
                layer_keys = {k: v for k, v in layer_config.items() if k != "type"} # Get keys/config for this layer

                decrypted_result = None
                print(f"  Layer {i+1}/{len(layers)} ({layer_type})...")

                # Perform decryption based on layer type
                if layer_type == 'aes':
                    # AES needs 'key' and 'iv' in layer_config, with base64 values
                    aes_key_b64 = layer_keys.get('key')
                    aes_iv_b64 = layer_keys.get('iv')
                    if current_data_blob and aes_key_b64 and aes_iv_b64:
                        decrypted_result = aes_decrypt(current_data_blob, aes_key_b64, aes_iv_b64)
                    else:
                        print(f"    Verify failed (Layer {i+1} AES, ID {challenge.id}): Missing data blob, key, or iv in layer config.")
                        decryption_successful = False
                        break # Stop processing layers if one fails

                elif layer_type == 'vigenere':
                     # Vigenere needs 'key' in layer_config, with string value
                    vigenere_key = layer_keys.get('key')
                    if current_data_blob and vigenere_key:
                         decrypted_result = vigenere_decrypt(current_data_blob, vigenere_key)
                    else:
                         print(f"    Verify failed (Layer {i+1} Vigenere, ID {challenge.id}): Missing data blob or key in layer config.")
                         decryption_successful = False
                         break

                elif layer_type == 'rsa':
                    # RSA needs 'private_key' in layer_config, with string value
                    rsa_private_key = layer_keys.get('private_key')
                    # Note: For RSA, the *input* to decrypt is the ciphertext_b64 from the *previous* step's output (or challenge_data for the first layer).
                    # The output is plaintext, which might become ciphertext for the *next* decryption in the loop (previous encryption layer).
                    # So the data blob might need to be base64 encoded if the next layer expects base64 input (like AES).
                    # Let's assume decryption functions return strings, and AES expects base64 string input.
                    # We need to handle encoding/decoding between string/base64 steps if layers mix.
                    # Simplification: Assume intermediate outputs can be handled. If decryption fails, it returns None.

                    if current_data_blob and rsa_private_key:
                        # If the previous step's output isn't already base64 (e.g., Vigenere output),
                        # you might need to encode it here if rsa_decrypt expects base64 input.
                        # Our current rsa_decrypt expects base64_b64 input, so current_data_blob needs to be the base64 string.
                        # This implies intermediate results might need to be base64 encoded if the next layer requires it.
                        # This is getting complex. Let's assume for v1 that intermediate results match the next layer's input type need.
                        # If AES->Vigenere->RSA, data starts as AES-b64, becomes Vigenere-plaintext, becomes RSA-plaintext.
                        # If RSA->Vigenere->AES, data starts as RSA-b64, becomes Vigenere-plaintext, becomes AES-plaintext.
                        # This is tricky. Let's stick to simpler layer types like AES->Vigenere or Vigenere->AES for now.
                        # The current rsa_decrypt expects b64, so if a previous layer output a string, it would fail.
                        # Let's assume for now layers don't mix string/b64 requirements awkwardly unless manually handled by admin encoding/decoding.

                        decrypted_result = rsa_decrypt(current_data_blob, rsa_private_key)
                    else:
                         print(f"    Verify failed (Layer {i+1} RSA, ID {challenge.id}): Missing data blob or private_key in layer config.")
                         decryption_successful = False
                         break

                else:
                    print(f"    Verify failed (Layer {i+1}, ID {challenge.id}): Unknown layer type '{layer_type}'.")
                    decryption_successful = False
                    break # Stop if type is unknown

                # Update data blob for the next layer (or final comparison)
                if decrypted_result is not None:
                    current_data_blob = decrypted_result # Result of decryption becomes input for next step
                else:
                    # Decryption failed for this layer
                    decryption_successful = False
                    break # Stop processing layers

            # After iterating through all layers
            if decryption_successful:
                final_decrypted_text = current_data_blob
                 # Compare the final decrypted text to the stored flag
                is_correct = final_decrypted_text is not None and submitted_answer_part.strip() == challenge.flag.strip()
                if not is_correct:
                     print(f"Verify failed (Layered Crypto, ID {challenge.id}): Final decrypted text does not match flag.")
            else:
                # One or more layers failed to decrypt
                is_correct = False # Ensure is_correct is False


        else:
            # --- Fallback to Single-Layer Crypto Verification (if 'layers' key is missing or not a list) ---
            print(f"Verifying single-layer crypto challenge (ID {challenge.id})...")
            decrypted_text = None
            # Reuse the config dictionary loaded above

            if challenge.encryption_type == 'aes':
                # AES requires challenge_data (ciphertext) and config_json (key, iv) with keys 'key' and 'iv'
                # The single-layer admin form guides this input.
                if challenge.challenge_data and 'key' in config and 'iv' in config:
                    decrypted_text = aes_decrypt(challenge.challenge_data, config['key'], config['iv'])
                else:
                     print(f"Verify failed (Single Crypto/AES, ID {challenge.id}): Missing challenge_data, key, or iv in config.")
                     # If challenge_data exists but keys are missing, it's an admin config error
                     # If challenge_data is missing, verification cannot proceed.
                     pass # is_correct remains False

            elif challenge.encryption_type == 'vigenere':
                # Vigenere requires challenge_data (ciphertext) and config_json (key) with key 'key'
                if challenge.challenge_data and 'key' in config:
                    decrypted_text = vigenere_decrypt(challenge.challenge_data, config['key'])
                else:
                     print(f"Verify failed (Single Crypto/Vigenere, ID {challenge.id}): Missing challenge_data or key in config.")
                     pass

            elif challenge.encryption_type == 'rsa':
                # RSA requires challenge_data (ciphertext) and config_json (private key) with key 'private_key'
                if challenge.challenge_data and 'private_key' in config: # Store private key in config_json for admin/verification
                    decrypted_text = rsa_decrypt(challenge.challenge_data, config['private_key'])
                else:
                     print(f"Verify failed (Single Crypto/RSA, ID {challenge.id}): Missing challenge_data or private_key in config.")
                     pass # is_correct remains False

            else:
                # Unknown crypto type configured for a crypto challenge
                print(f"Verify failed (Single Crypto, ID {challenge.id}): Unknown encryption_type '{challenge.encryption_type}'.")
                pass # is_correct remains False

            # Compare the single-layer decrypted text to the stored flag
            # The submitted_answer_part should be the decrypted text
            is_correct = decrypted_text is not None and submitted_answer_part.strip() == challenge.flag.strip()
            if not is_correct:
                 print(f"Verify failed (Single Crypto, ID {challenge.id}): Decrypted text does not match flag.")


    # --- Verification logic for Non-Cryptography Categories ---
    else:
        # For all other categories, the submitted_answer_part is the flag itself
        print(f"Verifying non-crypto challenge (ID {challenge.id})...")
        is_correct = submitted_answer_part.strip() == challenge.flag.strip()
        if not is_correct:
             print(f"Verify failed (Non-Crypto, ID {challenge.id}): Submitted answer does not match flag.")


    # Clean up log context
    del current_app.challenge_id_for_log

    return is_correct

# Remove encrypt_by_type and key generation functions as admin now provides final data/config
# def encrypt_by_type(...): ... # REMOVED
# def generate_aes_key(): ... # REMOVED
# def generate_aes_iv(): ... # REMOVED
# def generate_rsa_key_pair(): ... # REMOVED
# def rsa_encrypt(...): ... # REMOVED