# create_layered_crypto_challenge.py

import secrets
import base64
import json
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
# Use Crypto.PublicKey and Crypto.Cipher for RSA
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


# --- Encryption Functions Adapted for Layering ---

# AES Encryption Layer
def aes_encrypt_layer(data_to_encrypt):
    """Encrypt bytes using AES-CBC, return base64 ciphertext and config."""
    # Ensure data_to_encrypt is bytes
    if isinstance(data_to_encrypt, str):
        data_to_encrypt = data_to_encrypt.encode('utf-8')

    key = get_random_bytes(16)  # Generate new key per layer
    iv = get_random_bytes(16)   # Generate new IV per layer

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data_to_encrypt, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)

    # Output base64 encoded ciphertext as the data for the next layer
    output_data = base64.b64encode(ciphertext).decode('utf-8')

    # Store keys as base64 for admin UI
    layer_config = {
        'key_b64': base64.b64encode(key).decode('utf-8'),
        'iv_b64': base64.b64encode(iv).decode('utf-8')
    }

    return output_data, layer_config

# Vigenère Encryption Layer
def vigenere_encrypt_layer(data_to_encrypt):
    """Encrypt string using Vigenère, return string ciphertext and config."""
    # Ensure data_to_encrypt is string
    if isinstance(data_to_encrypt, bytes):
        data_to_encrypt = data_to_encrypt.decode('utf-8')

    # Generate a random letter key
    letters = 'abcdefghijklmnopqrstuvwxyz'
    key = ''.join(secrets.choice(letters) for _ in range(10)) # Random 10-letter key

    # Ensure key is only letters and uppercase for encryption logic
    key = ''.join(c for c in key if c.isalpha()).upper()
    if not key:
         print("Warning: Generated Vigenere key has no letters. Using default 'KEY'.")
         key = "KEY"


    ciphertext = ""
    key_index = 0

    for char in data_to_encrypt:
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

    # Output is the raw ciphertext string
    output_data = ciphertext

    layer_config = {'key': key} # Store the raw key

    return output_data, layer_config


# RSA Encryption Layer
def rsa_encrypt_layer(data_to_encrypt, key_size=2048):
    """Encrypt bytes using RSA Public key, return base64 ciphertext and key pair config."""
    # Ensure data_to_encrypt is bytes
    if isinstance(data_to_encrypt, str):
        data_to_encrypt = data_to_encrypt.encode('utf-8')

    # Generate a new RSA key pair per layer
    key = RSA.generate(key_size)
    private_key = key.export_key().decode('utf-8')
    public_key = key.publickey().export_key().decode('utf-8')

    try:
        # Create PKCS#1 OAEP cipher and encrypt
        cipher = PKCS1_OAEP.new(RSA.import_key(public_key))

        # RSA has a limit on data size. Truncate if necessary for simulation.
        max_size = RSA.import_key(public_key).size_in_bytes() - 42 # OAEP padding size
        if len(data_to_encrypt) > max_size:
            print(f"Warning: Data for RSA layer is too large ({len(data_to_encrypt)} bytes > {max_size} bytes). Truncating...")
            data_to_encrypt = data_to_encrypt[:max_size] # Truncate

        ciphertext = cipher.encrypt(data_to_encrypt)

        # Output base64 encoded ciphertext as the data for the next layer
        output_data = base64.b64encode(ciphertext).decode('utf-8')

        # Store the full key pair config (public key might be needed for challenge data display)
        layer_config = {
            'public_key': public_key,
            'private_key': private_key # Admin needs private key for verification config
        }

        return output_data, layer_config
    except Exception as e:
        print(f"RSA Encryption Layer Error: {e}")
        return None, None # Indicate failure

# --- Main Script ---

def run_layered_encryption_script():
    print("--- Layered Cryptography Challenge Generator ---")

    original_plaintext = input("Enter the original plaintext (the flag's content): ")
    if not original_plaintext:
        print("Plaintext cannot be empty. Exiting.")
        return

    current_data = original_plaintext.encode('utf-8') # Start with plaintext as bytes for first encryption
    layer_details = [] # List to store details for each layer

    print("\nAvailable encryption types: AES, Vigenere, RSA")
    print("Enter types one by one. Enter 'done' when finished.")

    layer_number = 1
    while True:
        layer_type_input = input(f"Layer {layer_number} type (AES, Vigenere, RSA, or done): ").strip().lower()

        if layer_type_input == 'done':
            if layer_number == 1:
                print("No encryption layers added. Exiting.")
                return
            break
        elif layer_type_input not in ['aes', 'vigenere', 'rsa']:
            print("Invalid type. Please enter AES, Vigenere, RSA, or done.")
            continue

        print(f"Applying {layer_type_input.upper()} to data...")

        output_data = None
        layer_config = None

        # --- Apply Encryption Layer ---
        try:
            if layer_type_input == 'aes':
                 # AES takes bytes, current_data should be bytes
                 output_data, layer_config = aes_encrypt_layer(current_data)
            elif layer_type_input == 'vigenere':
                 # Vigenere takes string, ensure current_data is string
                 if isinstance(current_data, bytes): # If previous layer was AES/RSA (base64 bytes)
                     current_data = base64.b64decode(current_data).decode('utf-8', errors='ignore') # Decode base64, ignore errors
                 output_data, layer_config = vigenere_encrypt_layer(current_data)
            elif layer_type_input == 'rsa':
                 # RSA takes bytes, ensure current_data is bytes
                 if isinstance(current_data, str): # If previous layer was Vigenere
                      current_data = current_data.encode('utf-8')
                 output_data, layer_config = rsa_encrypt_layer(current_data) # RSA encrypts bytes


            if output_data is None or layer_config is None:
                 print(f"Error applying {layer_type_input.upper()} layer. Aborting.")
                 return # Exit if a layer fails

            # Store details for this layer
            layer_details.append({
                'number': layer_number,
                'type': layer_type_input.upper(),
                'config': layer_config,
                'output_preview': str(output_data)[:50] + ('...' if len(str(output_data)) > 50 else '') # Store a preview
            })

            # Update current_data for the next iteration
            # Ensure format is appropriate for the NEXT potential layer
            # AES/RSA layers output base64 *strings*. Vigenere outputs a raw string.
            # Store the output data in a consistent format, like string (Base64 or raw)
            if isinstance(output_data, bytes): # Should not happen with base64 outputs, but safety
                 current_data = output_data.decode('utf-8', errors='ignore')
            else:
                 current_data = output_data # It's already a string (Base64 or Vigenere)


            layer_number += 1

        except Exception as e:
            print(f"An unexpected error occurred during layer {layer_number} ({layer_type_input.upper()}): {e}")
            import traceback
            traceback.print_exc()
            return # Exit on unexpected errors


    final_ciphertext = current_data # The output of the last layer


    # --- Output Results for Admin UI ---
    print("\n--- Challenge Data Ready for Admin Panel ---")
    print(f"Original Plaintext (Flag Content): {original_plaintext}")
    print(f"\nFinal Ciphertext (Challenge Data):")
    print(final_ciphertext)

    print("\nLayers Applied (Sequence and Config):")
    config_list = [] # Prepare list for config_json
    layer_sequence = [] # Prepare sequence string

    for i, layer in enumerate(layer_details):
        print(f"  Layer {layer['number']} ({layer['type']}):")
        print(f"    Config: {json.dumps(layer['config'], indent=2)}")
        # For RSA, also print the public key separately if needed for challenge description
        if layer['type'] == 'RSA' and 'public_key' in layer['config']:
             print("    RSA Public Key (for user info):")
             print(layer['config']['public_key'])

        config_list.append({'layer': layer['number'], 'type': layer['type'], 'config': layer['config']})
        layer_sequence.append(layer['type'])

    print("\n--> Copy/Paste into Admin 'Create Challenge' Form:")
    print(f"Category: Cryptography")
    print(f"Difficulty: (Choose Easy/Medium/Hard based on complexity/layers)")
    print(f"Title: (e.g., Layered AES, Vigenere, RSA)")
    print(f"Description: Describe the challenge. Mention the layers applied: {' -> '.join(layer_sequence)}. Tell them to reverse it.")
    print(f"Flag (Solution): {original_plaintext}")
    print(f"Challenge Data/Instructions: {final_ciphertext}") # Final output goes here
    print(f"Encryption Type: (Select 'aes' in the form, even though it's layered. Or maybe add 'layered' type?)") # Or leave empty if you don't require it for non-layered
    print(f"Configuration (JSON or Text):")
    print(json.dumps(config_list, indent=2)) # Store all layer configs as a JSON list

    print("\n--- Verification Notes ---")
    print("To verify a submitted Flag{ID_answer} for this challenge (ID will be assigned by DB):")
    print(f"1. Extract the 'answer' part from the flag: Flag{{ID_{original_plaintext}}}")
    print("2. Use the Configuration JSON (above) and apply the decryption in REVERSE order.")
    print("   - Start with the final ciphertext (Challenge Data).")
    print("   - Decrypt the LAST layer using its config.")
    print("   - Take the result, decrypt the SECOND TO LAST layer using its config.")
    print("   - Continue until you decrypt the FIRST layer.")
    print("3. The final decrypted text should match the original Plaintext you entered.")
    print("   Your app's verify_challenge_solution function will automate step 2 & 3.")


# Run the script if executed directly
if __name__ == "__main__":
    run_layered_encryption_script()
