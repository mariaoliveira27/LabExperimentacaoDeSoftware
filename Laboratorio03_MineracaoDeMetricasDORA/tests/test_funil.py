"""
Testes unitários para o módulo do Funil de Seleção e Descarte (funil.py).
Verifica a contabilização de etapas, motivos de descarte e relatórios.
"""

import os
import tempfile
from funil import FunilSelecao


def test_funil_etapas_e_descartes():
    funil = FunilSelecao(target_approved=2)

    # 4 candidatos iniciais
    funil.registrar_candidato_inicial({"full_name": "repo/1"})
    funil.registrar_candidato_inicial({"full_name": "repo/2"})
    funil.registrar_candidato_inicial({"full_name": "repo/3"})
    funil.registrar_candidato_inicial({"full_name": "repo/4"})

    # repo/4 descartado sem actions
    funil.registrar_descarte("repo/4", "2. GitHub Actions", "sem_github_actions")
    funil.aprovar_actions({"full_name": "repo/1"})
    funil.aprovar_actions({"full_name": "repo/2"})
    funil.aprovar_actions({"full_name": "repo/3"})

    # repo/3 descartado com menos de 5 releases
    funil.registrar_descarte("repo/3", "3. Releases na janela", "menos_de_5_releases_na_janela")
    funil.aprovar_releases({"full_name": "repo/1"})
    funil.aprovar_releases({"full_name": "repo/2"})

    # repo/1 e repo/2 aprovados
    funil.aprovar_repositorio({"full_name": "repo/1"})
    funil.aprovar_repositorio({"full_name": "repo/2"})

    tabela = funil.gerar_tabela_funil()
    assert len(tabela) == 4
    assert tabela[0]["total_restante"] == 4
    assert tabela[1]["total_restante"] == 3
    assert tabela[2]["total_restante"] == 2
    assert tabela[3]["total_restante"] == 2
    assert len(funil.descartes) == 2


def test_funil_salvar_relatorios():
    funil = FunilSelecao(target_approved=1)
    funil.registrar_candidato_inicial({"full_name": "repo/test"})
    funil.aprovar_actions({"full_name": "repo/test"})
    funil.aprovar_releases({"full_name": "repo/test"})
    funil.aprovar_repositorio({"full_name": "repo/test"})

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "funil.csv")
        md_path = os.path.join(tmpdir, "funil.md")
        disc_path = os.path.join(tmpdir, "descartes.csv")

        funil.salvar_relatorios(csv_path, md_path, disc_path)

        assert os.path.exists(csv_path)
        assert os.path.exists(md_path)
        assert os.path.exists(disc_path)

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Funil de Seleção" in content or "Funil de Sele" in content
            assert "Total aprovado para análise:" in content and "1" in content

