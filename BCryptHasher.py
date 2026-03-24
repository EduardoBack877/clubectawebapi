import bcrypt

class BcryptHasher:
    def __init__(self, rounds: int = 12):
        """
        Inicializa a classe com o número de rounds (complexidade) para o hashing.
        Um número maior de rounds aumenta a segurança, mas também o tempo de processamento.

        :param rounds: Número de rounds para o algoritmo bcrypt.
        """
        self.rounds = rounds

    def generate_hash(self, password: str) -> str:
        """
        Gera um hash seguro para a senha fornecida.

        :param password: A senha em texto plano.
        :return: O hash da senha em formato string.
        """
        salt = bcrypt.gensalt(self.rounds)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """
        Verifica se a senha fornecida corresponde ao hash armazenado.

        :param password: A senha em texto plano fornecida para verificação.
        :param stored_hash: O hash armazenado da senha.
        :return: True se a senha corresponder ao hash, False caso contrário.
        """
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

