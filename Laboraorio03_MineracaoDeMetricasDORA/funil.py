"""
Módulo de Gerenciamento do Funil de Seleção e Registro de Descartes.
Atende aos requisitos do Lab03:
- Aplicação estrita dos critérios de inclusão (Seção 3):
  1. Candidatos da busca inicial (stars > 1000)
  2. Uso de GitHub Actions (total_count > 0 em /actions/workflows)
  3. Mínimo de 5 releases válidas (draft=False, prerelease=False) na janela de 12 meses
  4. Mínimo de 50 workflow runs válidos no default branch (event=push) na janela
- Registro de log detalhado com motivos de descarte para cada repositório analisado
- Exportação automática do resumo do funil em CSV e Markdown para a Metodologia do artigo
"""

import os
import csv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class RegistroDescarte:
    full_name: str
    etapa: str
    motivo: str
    detalhes: str = ""


class FunilSelecao:
    def __init__(self, target_approved: int = 100):
        self.target_approved = target_approved
        self.candidatos_iniciais: List[Dict[str, Any]] = []
        self.com_actions: List[Dict[str, Any]] = []
        self.com_releases_suficientes: List[Dict[str, Any]] = []
        self.aprovados: List[Dict[str, Any]] = []
        self.descartes: List[RegistroDescarte] = []

    def registrar_candidato_inicial(self, repo: Dict[str, Any]):
        self.candidatos_iniciais.append(repo)

    def registrar_descarte(self, full_name: str, etapa: str, motivo: str, detalhes: str = ""):
        self.descartes.append(RegistroDescarte(
            full_name=full_name,
            etapa=etapa,
            motivo=motivo,
            detalhes=detalhes,
        ))

    def aprovar_actions(self, repo: Dict[str, Any]):
        self.com_actions.append(repo)

    def aprovar_releases(self, repo: Dict[str, Any]):
        self.com_releases_suficientes.append(repo)

    def aprovar_repositorio(self, repo: Dict[str, Any]):
        self.aprovados.append(repo)

    def gerar_tabela_funil(self) -> List[Dict[str, Any]]:
        """Gera os dados tabulares do funil com contagens e percentuais."""
        n_iniciais = len(self.candidatos_iniciais)
        n_actions = len(self.com_actions)
        n_releases = len(self.com_releases_suficientes)
        n_aprovados = len(self.aprovados)

        etapas = [
            {
                "etapa": "1. Candidatos da busca inicial (stars > 1000)",
                "total_restante": n_iniciais,
                "descartados": 0,
                "motivo_descarte": "-",
                "retencao_pct": 100.0 if n_iniciais > 0 else 0.0,
            },
            {
                "etapa": "2. Presença de GitHub Actions configurado",
                "total_restante": n_actions,
                "descartados": n_iniciais - n_actions,
                "motivo_descarte": "sem_github_actions",
                "retencao_pct": round((n_actions / n_iniciais * 100), 2) if n_iniciais > 0 else 0.0,
            },
            {
                "etapa": "3. Mínimo de 5 releases na janela (12 meses)",
                "total_restante": n_releases,
                "descartados": n_actions - n_releases,
                "motivo_descarte": "menos_de_5_releases_na_janela",
                "retencao_pct": round((n_releases / n_iniciais * 100), 2) if n_iniciais > 0 else 0.0,
            },
            {
                "etapa": "4. Mínimo de 50 workflow runs válidos no default branch",
                "total_restante": n_aprovados,
                "descartados": n_releases - n_aprovados,
                "motivo_descarte": "menos_de_50_runs_na_janela",
                "retencao_pct": round((n_aprovados / n_iniciais * 100), 2) if n_iniciais > 0 else 0.0,
            },
        ]
        return etapas

    def salvar_relatorios(
        self,
        caminho_funil_csv: str = "data/output/funil_selecao.csv",
        caminho_funil_md: str = "data/output/funil_selecao.md",
        caminho_descartes_csv: str = "data/output/descartes.csv",
    ):
        """Salva relatórios do funil em CSV, Markdown e o log de descartes."""
        os.makedirs(os.path.dirname(os.path.abspath(caminho_funil_csv)), exist_ok=True)

        tabela = self.gerar_tabela_funil()

        # Salva funil CSV
        with open(caminho_funil_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["etapa", "total_restante", "descartados", "motivo_descarte", "retencao_pct"],
            )
            writer.writeheader()
            writer.writerows(tabela)

        # Salva funil Markdown
        with open(caminho_funil_md, "w", encoding="utf-8") as f:
            f.write("# Funil de Seleção de Repositórios (Lab03)\n\n")
            f.write("A tabela abaixo detalha o funil de seleção com base nos critérios de inclusão:\n\n")
            f.write("| Etapa | Restantes | Descartados | Motivo Principal | Retenção Global (%) |\n")
            f.write("|---|---|---|---|---|\n")
            for linha in tabela:
                f.write(
                    f"| {linha['etapa']} | {linha['total_restante']} | {linha['descartados']} | "
                    f"`{linha['motivo_descarte']}` | {linha['retencao_pct']}% |\n"
                )
            f.write("\n")
            f.write(f"**Total aprovado para análise:** {len(self.aprovados)} repositórios.\n")

        # Salva descartes CSV
        with open(caminho_descartes_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["full_name", "etapa", "motivo", "detalhes"],
            )
            writer.writeheader()
            for d in self.descartes:
                writer.writerow({
                    "full_name": d.full_name,
                    "etapa": d.etapa,
                    "motivo": d.motivo,
                    "detalhes": d.detalhes,
                })
