def externa():
    def interna(ativo):
        if ativo:
            return 1
        return 0

    return interna
