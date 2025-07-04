#!/usr/bin/env python3
"""
Script simples para listar apenas os nomes das variáveis de um projeto GitLab.
"""

import gitlab
import sys
import argparse


def listar_nomes_variaveis(gitlab_url: str, project_id: str, token: str) -> None:
    """
    Lista apenas os nomes das variáveis de um projeto GitLab.

    Args:
        gitlab_url: URL do servidor GitLab
        project_id: ID do projeto no GitLab
        token: Token de acesso ao GitLab
    """
    try:
        # Conectar ao GitLab
        gl = gitlab.Gitlab(gitlab_url, private_token=token)

        # Obter o projeto
        project = gl.projects.get(project_id)

        # Obter todas as variáveis do projeto
        variaveis = project.variables.list(all=True)

        # Extrair apenas os nomes
        nomes = [var.key for var in variaveis]

        if nomes:
            print(f"Variáveis encontradas ({len(nomes)}):")
            for nome in sorted(nomes):
                print(f"  - {nome}")
        else:
            print("Nenhuma variável encontrada no projeto.")

    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lista os nomes das variáveis de um projeto GitLab.")
    parser.add_argument("gitlab_url", help="URL do servidor GitLab (ex: https://gitlab.com)")
    parser.add_argument("project_id", help="ID do projeto no GitLab")
    parser.add_argument("token", help="Token de acesso ao GitLab")

    args = parser.parse_args()

    listar_nomes_variaveis(args.gitlab_url, args.project_id, args.token)
