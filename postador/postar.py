"""
Posta (ou agenda) um vídeo em uma rede pelo Upload-Post.

Uso:  python postador/postar.py <youtube|instagram|tiktok> <pasta_do_job>

A pasta do job tem o vídeo e um job.json criado pela página:
{
  "arquivo": "video.mp4",
  "titulo": "Título do Short no YouTube",
  "legenda": "Legenda padrão #anime",
  "legendas": {"youtube": "", "instagram": "", "tiktok": ""},
  "redes": ["youtube", "instagram", "tiktok"],
  "agendar": "2026-11-13T18:30" ou null,
  "fuso": "America/Sao_Paulo",
  "ia": false
}
"""

import json
import mimetypes
import os
import sys
import time
import uuid
from pathlib import Path

import requests

API = "https://api.upload-post.com/api"
REDES = ("youtube", "instagram", "tiktok")


def log(msg):
    print(msg, flush=True)


def aviso(msg):
    print(f"::warning::{msg}", flush=True)


def erro(msg):
    print(f"::error::{msg}", flush=True)
    sys.exit(1)


def precisa(nome):
    valor = os.environ.get(nome, "").strip()
    if not valor:
        erro(f"Falta o secret {nome}. Veja o README, parte 'Configurar'.")
    return valor


def montar_campos(rede, job):
    """Campos do formulário do Upload-Post para uma rede."""
    legenda = (job.get("legendas") or {}).get(rede) or job.get("legenda", "")
    titulo = (job.get("titulo") or "").strip()

    campos = [("user", precisa("UPLOADPOST_USER")), ("platform[]", rede)]

    if rede == "youtube":
        # YouTube exige título (máx. 100 caracteres); a legenda vira descrição
        campos += [
            ("title", (titulo or legenda or "Novo vídeo")[:100]),
            ("youtube_description", legenda),
            ("privacyStatus", "public"),
            ("selfDeclaredMadeForKids", "false"),
        ]
    elif rede == "instagram":
        campos += [("title", legenda), ("instagram_title", legenda), ("media_type", "REELS"), ("share_to_feed", "true")]
        if job.get("ia"):
            campos.append(("is_ai_generated", "true"))
    elif rede == "tiktok":
        campos += [("title", legenda), ("tiktok_title", legenda[:2200])]
        if job.get("ia"):
            campos.append(("is_aigc", "true"))

    if job.get("agendar"):
        campos += [("scheduled_date", job["agendar"]), ("timezone", job.get("fuso") or "America/Sao_Paulo")]
    else:
        campos.append(("async_upload", "true"))
    return campos


def esperar(chave, request_id, rede):
    """Acompanha o envio até terminar (máx. ~25 min)."""
    for _ in range(150):
        time.sleep(10)
        r = requests.get(
            f"{API}/uploadposts/status",
            headers={"Authorization": f"Apikey {chave}"},
            params={"request_id": request_id},
            timeout=30,
        )
        if r.status_code == 404:
            continue  # ainda não registrado
        dados = r.json()
        status = dados.get("status")
        log(f"{rede}: {status}")
        if status in ("completed", "failed"):
            return dados
    erro(f"{rede}: o Upload-Post demorou demais. Confira no painel deles antes de postar de novo.")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in REDES:
        erro("Uso: python postador/postar.py <youtube|instagram|tiktok> <pasta_do_job>")
    rede, pasta = sys.argv[1], Path(sys.argv[2])

    job = json.loads((pasta / "job.json").read_text(encoding="utf-8"))
    video = pasta / job.get("arquivo", "video.mp4")
    if not video.exists():
        erro(f"Vídeo não encontrado: {video}")

    chave = precisa("UPLOADPOST_API_KEY")
    campos = montar_campos(rede, job)
    request_id = f"{os.environ.get('GITHUB_RUN_ID', 'local')}-{rede}-{uuid.uuid4().hex[:6]}"
    campos.append(("request_id", request_id))

    quando = f"agendado para {job['agendar']}" if job.get("agendar") else "agora"
    log(f"Enviando {video.name} ({video.stat().st_size / 1e6:.1f} MB) para o {rede}, {quando}")

    with open(video, "rb") as f:
        r = requests.post(
            f"{API}/upload",
            headers={"Authorization": f"Apikey {chave}", "Idempotency-Key": request_id},
            data=campos,
            files={"video": (video.name, f, mimetypes.guess_type(video.name)[0] or "video/mp4")},
            timeout=600,
        )

    try:
        dados = r.json()
    except ValueError:
        dados = {"texto": r.text[:500]}

    if r.status_code == 401:
        erro("Chave do Upload-Post inválida (secret UPLOADPOST_API_KEY).")
    if r.status_code == 403:
        erro(f"Upload-Post bloqueou o {rede}. No plano grátis o TikTok não funciona. Resposta: {dados}")
    if r.status_code == 429:
        erro(f"Limite mensal do Upload-Post atingido: {dados.get('usage')}")
    if r.status_code >= 300:
        erro(f"Upload-Post recusou ({r.status_code}): {dados}")

    if r.status_code == 202 or dados.get("job_id"):
        log(f"{rede}: agendado para {dados.get('scheduled_date', job.get('agendar'))} (job {dados.get('job_id')})")
        return

    # Resultado direto (envio rápido) ou acompanhamento em segundo plano
    if not dados.get("results"):
        dados = esperar(chave, dados.get("request_id") or request_id, rede)

    resultados = dados.get("results") or {}
    itens = resultados.values() if isinstance(resultados, dict) else resultados
    for item in itens:
        if item.get("skipped"):
            erro(f"{rede}: conta não conectada no Upload-Post ({item.get('skip_reason')}).")
        if not item.get("success"):
            erro(f"{rede}: falhou: {item.get('message') or item.get('error')}")
        link = item.get("post_url") or item.get("url")
        log(f"{rede} ok: {link or 'publicado'}")
        for w in item.get("warnings") or []:
            aviso(f"{rede}: {w}")

    if dados.get("status") == "failed":
        erro(f"{rede}: falhou: {dados.get('message')}")


if __name__ == "__main__":
    main()
