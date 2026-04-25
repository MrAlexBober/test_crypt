"""
Генерация ECDH P-256 ключей для ручной вставки в чат.

Требует: pip install cryptography
Использование: python generate_keys.py
"""

import json
import base64
from cryptography.hazmat.primitives.asymmetric.ec import generate_private_key, SECP256R1
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption


def int_to_base64url(n, length):
    """Конвертируем большое число в Base64url (формат JWK)."""
    b = n.to_bytes(length, byteorder="big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def generate():
    # Шаг 1: генерируем приватный ключ на кривой P-256 (она же secp256r1)
    private_key = generate_private_key(curve=SECP256R1())

    # Шаг 2: получаем публичный ключ из приватного
    public_key = private_key.public_key()

    # Шаг 3: извлекаем числа (x, y) из публичного ключа и (d) из приватного
    priv_numbers = private_key.private_numbers()
    pub_numbers  = public_key.public_key().public_numbers() if hasattr(public_key, "public_key") else priv_numbers.public_numbers

    x = priv_numbers.public_numbers.x
    y = priv_numbers.public_numbers.y
    d = priv_numbers.private_value

    # P-256 использует 32-байтные числа
    BYTE_LEN = 32

    # Шаг 4: собираем JWK (JSON Web Key) — формат понятный браузеру
    jwk_private = {
        "kty": "EC",           # тип ключа: эллиптическая кривая
        "crv": "P-256",        # конкретная кривая
        "d":   int_to_base64url(d, BYTE_LEN),   # приватная часть
        "x":   int_to_base64url(x, BYTE_LEN),   # публичная X
        "y":   int_to_base64url(y, BYTE_LEN),   # публичная Y
        "key_ops": ["deriveKey"]
    }

    # Шаг 5: публичный ключ в raw формате (65 байт: 0x04 + X + Y)
    # Именно этот формат используется при обмене в нашем чате (base64)
    raw_public = public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.b64encode(raw_public).decode()

    return jwk_private, pub_b64


if __name__ == "__main__":
    print("Генерация ECDH P-256 ключей...\n")

    jwk, pub_b64 = generate()

    print("=" * 60)
    print("ПРИВАТНЫЙ КЛЮЧ (JWK) — вставь в поле 'Вставить свой ключ':")
    print("=" * 60)
    print(json.dumps(jwk, indent=2))

    print()
    print("=" * 60)
    print("ПУБЛИЧНЫЙ КЛЮЧ (Base64 raw) — для справки:")
    print("=" * 60)
    print(pub_b64)

    print()
    print("ВАЖНО: приватный ключ ('d') никому не передавай.")
    print("Публичный ключ браузер вычислит из JWK автоматически.")

    # Сохраняем в файл для удобства
    with open("my_key.json", "w") as f:
        json.dump(jwk, f, indent=2)
    print("\nПриватный ключ также сохранён в my_key.json")
