from pwdlib import PasswordHash

# Argon2id con parámetros recomendados. Se instancia una sola vez.
_password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Devuelve el hash seguro (con salt incluido) de una contraseña en texto plano."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba si la contraseña en texto plano corresponde al hash almacenado."""
    return _password_hasher.verify(plain_password, hashed_password)
