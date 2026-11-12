"""
Roda a cada 15 minutos pelo GitHub Actions (agendador.yml).

Procura as branches fila/... que estão esperando um horário agendado.
Quando chega a hora, dispara o workflow "Postar" naquela branch.
"""

import base64
import json
import os
from datetime import datetime, timedelta
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


def ja_disparado(branch):
    runs = gh("GET", "/actions/workflows/postar.yml/runs", params={"branch": branch, "event": "workflow_dispatch", "per_page": 5})
    return runs["total_count"] > 0


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

        # Dispara até 5 min antes, porque o post leva alguns minutos
        if hora - timedelta(minutes=5) > agora:
            print(f"{branch}: agendado para {job['agendar']}, ainda não")
            continue
        if ja_disparado(branch):
            print(f"{branch}: já disparado, esperando terminar")
            continue

        gh("POST", "/actions/workflows/postar.yml/dispatches", json={"ref": branch})
        print(f"{branch}: hora chegou, disparando postagem")


if __name__ == "__main__":
    main()
