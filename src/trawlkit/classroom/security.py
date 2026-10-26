"""Contraseñas, tokens, códigos y semillas del aula (sólo biblioteca estándar)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
#: Alfabeto de los códigos de curso e invitación (sin 0/O ni 1/I/L, que se confunden).
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def hash_password(password: str) -> str:
    """Hash scrypt con sal: ``scrypt$N$r$p$sal$hash`` (base64)."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b64 = base64.b64encode
    return f"scrypt${_N}${_R}${_P}${b64(salt).decode()}${b64(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """Si ``password`` coincide con el hash guardado (comparación en tiempo constante)."""
    try:
        kind, n, r, p, salt, digest = stored.split("$")
        if kind != "scrypt":
            return False
        got = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, base64.b64decode(digest))


def new_token() -> str:
    """Token de sesión opaco (32 bytes, URL-safe)."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """Hash SHA-256 del token: es lo único que guarda la base."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_code(length: int = 8) -> str:
    """Código legible para compartir (curso o invitación)."""
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def normalise_code(code: str) -> str:
    """Código en mayúsculas y sin espacios ni guiones."""
    return "".join(c for c in code.upper() if c.isalnum())


def student_seed(secret: str, assignment_id: int, user_id: int, item: int) -> int:
    """Semilla de los datos de un alumno para un ítem (estable y distinta por alumno)."""
    msg = f"{assignment_id}:{user_id}:{item}".encode()
    digest = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    return 1 + int.from_bytes(digest[:4], "big") % (2**31 - 2)
