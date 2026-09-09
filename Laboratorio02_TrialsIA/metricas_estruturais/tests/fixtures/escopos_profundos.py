class Caixa:
    def simples(self):
        return 1

    def decidir(self, valor):
        if valor:
            return valor
        return 0

    class Interna:
        async def acao(self, valor):
            if valor:
                return valor
            return None


def criar():
    class Local:
        def metodo(self):
            def profunda():
                def folha(valor):
                    if valor:
                        return valor
                    return 0

                return folha

            return profunda

    return Local
