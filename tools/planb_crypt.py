"""Klot's own voice recording travels to the runner encrypted (the repo is public): AES-256-GCM, a one-time key that is
given to the run as an input and read from the event file, never printed.
python tools/planb_crypt.py enc <in> <out.enc>  -> prints the key (hex) once, locally
python tools/planb_crypt.py dec <in.enc> <out>  (key from $GITHUB_EVENT_PATH inputs.key)"""
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if sys.argv[1] == "enc":
    k = AESGCM.generate_key(bit_length=256)
    n = os.urandom(12)
    data = open(sys.argv[2], "rb").read()
    open(sys.argv[3], "wb").write(n + AESGCM(k).encrypt(n, data, None))
    print(k.hex())
else:
    k = bytes.fromhex(json.load(open(os.environ["GITHUB_EVENT_PATH"]))["inputs"]["key"])
    blob = open(sys.argv[2], "rb").read()
    open(sys.argv[3], "wb").write(AESGCM(k).decrypt(blob[:12], blob[12:], None))
