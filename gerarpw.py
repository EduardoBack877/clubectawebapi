from passlib.hash import argon2

from BCryptHasher import BcryptHasher

hasher = BcryptHasher(rounds=12)

senha_texto = "eduardo"
senha_hash = hasher.generate_hash(senha_texto)
print (senha_hash)