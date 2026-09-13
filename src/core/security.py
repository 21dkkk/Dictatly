"""
Windows DPAPI secure storage for API keys and sensitive tokens.
Uses CryptProtectData / CryptUnprotectData via ctypes.
"""

import base64
import ctypes
from ctypes import wintypes
from typing import Optional

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]

CryptProtectData = ctypes.windll.crypt32.CryptProtectData
CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),     # pDataIn
    wintypes.LPCWSTR,              # szDataDescr
    ctypes.POINTER(DATA_BLOB),     # pOptionalEntropy
    ctypes.c_void_p,               # pvReserved
    ctypes.c_void_p,               # pPromptStruct
    wintypes.DWORD,                # dwFlags
    ctypes.POINTER(DATA_BLOB)      # pDataOut
]
CryptProtectData.restype = wintypes.BOOL

CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),     # pDataIn
    ctypes.POINTER(wintypes.LPWSTR), # ppszDataDescr
    ctypes.POINTER(DATA_BLOB),     # pOptionalEntropy
    ctypes.c_void_p,               # pvReserved
    ctypes.c_void_p,               # pPromptStruct
    wintypes.DWORD,                # dwFlags
    ctypes.POINTER(DATA_BLOB)      # pDataOut
]
CryptUnprotectData.restype = wintypes.BOOL

LocalFree = ctypes.windll.kernel32.LocalFree
LocalFree.argtypes = [ctypes.c_void_p]
LocalFree.restype = ctypes.c_void_p

CRYPTPROTECT_UI_FORBIDDEN = 0x01

def encrypt_secret(plaintext: str) -> str:
    """Encrypts plaintext string using current user's DPAPI key. Returns base64 string."""
    if not plaintext:
        return ""
    data_bytes = plaintext.encode("utf-8")
    in_blob = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()
    
    success = CryptProtectData(
        ctypes.byref(in_blob),
        "Dictatly_Key",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob)
    )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    
    encrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    LocalFree(out_blob.pbData)
    return base64.b64encode(encrypted_bytes).decode("ascii")

def decrypt_secret(encrypted_base64: str) -> str:
    """Decrypts base64 string encrypted with DPAPI. Returns plaintext string."""
    if not encrypted_base64:
        return ""
    try:
        encrypted_bytes = base64.b64decode(encrypted_base64)
        in_blob = DATA_BLOB(len(encrypted_bytes), ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        
        success = CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(out_blob)
        )
        if not success:
            return ""
        
        decrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        LocalFree(out_blob.pbData)
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return ""
