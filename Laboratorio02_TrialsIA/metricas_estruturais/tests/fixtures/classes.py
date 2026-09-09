class Painel:
    def titulo(self):
        return "Painel"

    def estado(self, ativo):
        if ativo:
            return "ativo"
        return "inativo"
