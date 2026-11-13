"""
Reserva do agendamento (agendador.yml, de hora em hora).

O normal é o próprio workflow "Postar" esperar até a hora. Se essa espera
for interrompida, este script acha posts atrasados nas branches fila/... e
dispara o "Postar" de novo, desde que não haja nenhuma execução ativa.
"""

import base64
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

REPO = os.environ["GITHUB_REPOSITORY"]
API = f"https://api.github.com/repos/{REPO}"
CAB = {
    "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def gh(metodo, caminho, **kw):
    r = requests.request(metodo, f"{API}{caminho}", headers=CAB, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.content else None


def branches_na_fila():
    nomes, pagina = [], 1
    while True:
        lote = gh("GET", f"/branches?per_page=100&page={pagina}")
        nomes += [b["name"] for b in lote if b["name"].startswith("fila/")]
        if len(lote) < 100:
            return nomes
        pagina += 1


def tem_execucao_ativa(branch):
    runs = gh("GET", "/actions/workflows/postar.yml/runs", params={"branch": branch, "per_page": 20})
    return any(r["status"] != "completed" for r in runs["workflow_runs"])


def main():
    agora = datetime.now(ZoneInfo("UTC"))
    for branch in branches_na_fila():
        try:
            arq = gh("GET", "/contents/fila/job.json", params={"ref": branch})
            job = json.loads(base64.b64decode(arq["content"]))
        except Exception as e:  # branch sem job.json ou quebrada
            print(f"{branch}: ignorada ({e})")
            continue

        if not job.get("agendar"):
            continue  # post imediato, o próprio push já cuida
        hora = datetime.fromisoformat(job["agendar"]).replace(tzinfo=ZoneInfo(job.get("fuso") or "America/Sao_Paulo"))

        if hora > agora:
            print(f"{branch}: agendado para {job['agendar']}, ainda não")
            continue
        if tem_execucao_ativa(branch):
            print(f"{branch}: já tem execução ativa (esperando ou postando)")
            continue

        gh("POST", "/actions/workflows/postar.yml/dispatches", json={"ref": branch})
        print(f"{branch}: hora chegou, disparando postagem")


if __name__ == "__main__":
    main()
