#!/usr/bin/env python3
"""Generate an Ed25519 update signing keypair.

Store the private value only in GitHub Actions secret UPDATE_SIGNING_PRIVATE_KEY_B64.
Commit the public value to updates.public_key in the release configuration.
"""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


private = Ed25519PrivateKey.generate()
private_raw = private.private_bytes_raw()
public_raw = private.public_key().public_bytes_raw()
print("UPDATE_SIGNING_PRIVATE_KEY_B64=" + base64.b64encode(private_raw).decode())
print("UPDATE_SIGNING_PUBLIC_KEY_B64=" + base64.b64encode(public_raw).decode())
