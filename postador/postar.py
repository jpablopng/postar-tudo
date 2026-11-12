"""
Posta um vídeo em uma rede.

Uso:  python postador/postar.py <youtube|instagram|tiktok> <pasta_do_job>

YouTube e TikTok vão pelo DarkPost (grátis, 1000 posts/mês).
Instagram vai pela API oficial do Instagram (secret IG_ACCESS_TOKEN).
Se esse secret não existir, tenta o Upload-Post (10 grátis por mês).

O agendamento é feito pelo próprio repositório (postador/agendador.py), então
aqui o post sempre sai "agora".

job.json (criado pela página):
{
  "arquivo": "video.mp4",
  "titulo": "Título do Short no YouTube",
  "legenda": "Legenda padrão #anime",
  "legendas": {"youtube": "", "instagram": "", "tiktok": ""},
  "redes": ["youtube", "tiktok"],
  "agendar": "2026-11-13T18:30:00" ou null,
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

DARKPOST = "https://darkpost.app/api/rest/providers"
UPLOADPOST = "https://api.upload-post.com/api"
GRAPH_IG = "https://graph.instagram.com/v23.0"
GRAPH_FB = "https://graph.facebook.com/v23.0"
RUPLOAD_IG = "https://rupload.facebook.com/ig-api-upload/v23.0"
REDES = ("youtube", "instagram", "tiktok")


# ---------------------------------------------------------------- utilidades

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


def legenda_de(job, rede):
    return (job.get("legendas") or {}).get(rede) or job.get("legenda", "")


def desembrulhar(resposta):
    """A API do DarkPost devolve {result: {data: ...}} (tRPC). Tira as camadas."""
    dados = resposta
    for chave in ("result", "data"):
        if isinstance(dados, dict) and chave in dados:
            dados = dados[chave]
    return dados


# ---------------------------------------------------------------- DarkPost

def darkpost(metodo, rota, chave, **kw):
    r = requests.request(
        metodo,
        f"{DARKPOST}/{rota}",
        headers={"x-api-token": chave, "Accept": "application/json"},
        timeout=kw.pop("timeout", 120),
        **kw,
    )
    if r.status_code == 401:
        erro("DarkPost recusou a chave (secret DARKPOST_API_KEY errado ou apagado).")
    try:
        corpo = r.json()
    except ValueError:
        corpo = {"texto": r.text[:500]}
    if r.status_code >= 300:
        erro(f"DarkPost respondeu {r.status_code} em {rota}: {corpo}")
    return desembrulhar(corpo)


def escolher_conta(chave, rede):
    """Usa DARKPOST_ACCOUNT_ID se existir; senão pega a conta conectada."""
    fixo = os.environ.get("DARKPOST_ACCOUNT_ID", "").strip()
    if fixo:
        return fixo
    dados = darkpost("GET", "GetAllProvidersFromAccount", chave)
    contas = dados.get("accounts", dados) if isinstance(dados, dict) else dados
    if not contas:
        erro("Nenhuma conta conectada no DarkPost.")

    # Mostra no log o que existe (só ids, nomes e redes), para conferir
    def resumo(c):
        return {k: c.get(k) for k in ("id", "name", "username", "provider", "platform", "providerIdentifier") if c.get(k)}
    log("Contas no DarkPost: " + json.dumps([resumo(c) for c in contas], ensure_ascii=False))

    # Prefere a conta da mesma rede, se a API informar a rede de cada conta
    for c in contas:
        texto = json.dumps(c).lower()
        if rede in texto and c.get("id"):
            return c["id"]
    return contas[0]["id"]


def postar_darkpost(rede, job, video):
    chave = precisa("DARKPOST_API_KEY")
    tipo = mimetypes.guess_type(video.name)[0] or "video/mp4"

    # 1) pede o link temporário de upload
    link = darkpost("POST", "upload/createObjectLinkS3", chave, json={"fileName": video.name, "fileType": tipo})
    if not link.get("uploadUrl") or not link.get("key"):
        erro(f"DarkPost não devolveu link de upload: {link}")

    # 2) sobe o arquivo
    log("Subindo o vídeo para o DarkPost...")
    with open(video, "rb") as f:
        up = requests.put(link["uploadUrl"], data=f, headers={"Content-Type": link.get("contentType") or tipo}, timeout=900)
    if up.status_code >= 300:
        erro(f"Falha ao subir o vídeo ({up.status_code}): {up.text[:300]}")

    # 3) publica agora
    corpo = {
        "videoKey": link["key"],
        "accountId": escolher_conta(chave, rede),
        "platforms": [rede],
        "caption": legenda_de(job, rede),
    }
    if rede == "youtube":
        corpo["title"] = (job.get("titulo") or legenda_de(job, rede) or "Novo vídeo")[:100]
    if rede == "tiktok":
        corpo["privacyLevel"] = "PUBLIC_TO_EVERYONE"

    log(f"Publicando no {rede}...")
    res = darkpost("POST", "upload/publishPost", chave, json=corpo, timeout=600)

    resultados = res.get("results") or []
    if not resultados:
        if res.get("published") or res.get("successful"):
            log(f"{rede} ok")
            return
        erro(f"{rede}: resposta inesperada do DarkPost: {res}")
    for item in resultados:
        if not item.get("success"):
            erro(f"{rede}: falhou no DarkPost: {item.get('error')}")
        log(f"{rede} ok: {item.get('linkVideo') or item.get('postId') or 'publicado'}")


# ---------------------------------------------------------------- Instagram (API oficial)

def postar_instagram(job, video):
    token = "".join(precisa("IG_ACCESS_TOKEN").split())  # tira espaços e quebras de linha coladas sem querer
    cab = {"Authorization": f"Bearer {token}"}

    # Token "IG..." (login do Instagram) usa graph.instagram.com.
    # Token "EA..." (login unificado / usuário do sistema) usa graph.facebook.com.
    if token.startswith("IG"):
        graph = GRAPH_IG
        log("Instagram: token do tipo login do Instagram")
        eu = requests.get(f"{graph}/me", headers=cab, params={"fields": "user_id,username"}, timeout=30)
        if not eu.ok:
            erro(f"Instagram recusou o token. Gere outro no painel da Meta e atualize o secret IG_ACCESS_TOKEN. Resposta: {eu.text[:300]}")
        ig_id = eu.json()["user_id"]
        nome = eu.json().get("username")
    else:
        graph = GRAPH_FB
        log(f"Instagram: token do tipo Facebook/sistema (começa com {token[:2]}), tamanho {len(token)}")
        ig_id = os.environ.get("IG_USER_ID", "").strip()
        if not ig_id:
            erro("Falta IG_USER_ID (id da conta do Instagram que aparece no painel da Meta).")
        eu = requests.get(f"{graph}/{ig_id}", headers=cab, params={"fields": "username"}, timeout=30)
        if not eu.ok:
            erro(f"Instagram recusou o token. Gere outro no painel da Meta e atualize o secret IG_ACCESS_TOKEN. Resposta: {eu.text[:300]}")
        nome = eu.json().get("username")
    log(f"Instagram: conta @{nome}")

    # 1) cria o container do Reels para upload direto do arquivo
    dados = {"media_type": "REELS", "upload_type": "resumable", "caption": legenda_de(job, "instagram"), "share_to_feed": "true"}
    r = requests.post(f"{graph}/{ig_id}/media", headers=cab, data=dados, timeout=60)
    if not r.ok:
        erro(f"Instagram: erro ao criar o post: {r.text[:500]}")
    container = r.json()["id"]

    # 2) envia o arquivo
    log("Subindo o vídeo para o Instagram...")
    with open(video, "rb") as f:
        r = requests.post(
            f"{RUPLOAD_IG}/{container}",
            headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(video.stat().st_size)},
            data=f,
            timeout=900,
        )
    if not r.ok:
        erro(f"Instagram: erro no upload: {r.text[:500]}")

    # 3) espera o Instagram processar (até 15 min)
    for _ in range(90):
        time.sleep(10)
        s = requests.get(f"{graph}/{container}", headers=cab, params={"fields": "status_code,status"}, timeout=30).json()
        codigo = s.get("status_code")
        log(f"Instagram processando: {codigo}")
        if codigo == "FINISHED":
            break
        if codigo in ("ERROR", "EXPIRED"):
            erro(f"Instagram recusou o vídeo: {s.get('status')}. Confira se é MP4 vertical, 3 a 90 s.")
    else:
        erro("Instagram demorou demais para processar o vídeo.")

    # 4) publica
    r = requests.post(f"{graph}/{ig_id}/media_publish", headers=cab, data={"creation_id": container}, timeout=60)
    if not r.ok:
        erro(f"Instagram: erro ao publicar: {r.text[:500]}")
    media_id = r.json().get("id")
    link = requests.get(f"{graph}/{media_id}", headers=cab, params={"fields": "permalink"}, timeout=30).json().get("permalink")
    log(f"instagram ok: {link or media_id}")


# ---------------------------------------------------------------- Upload-Post (Instagram, alternativa)

def postar_uploadpost(rede, job, video):
    chave = precisa("UPLOADPOST_API_KEY")
    legenda = legenda_de(job, rede)
    request_id = f"{os.environ.get('GITHUB_RUN_ID', 'local')}-{rede}-{uuid.uuid4().hex[:6]}"
    campos = [
        ("user", precisa("UPLOADPOST_USER")),
        ("platform[]", rede),
        ("title", legenda),
        ("instagram_title", legenda),
        ("media_type", "REELS"),
        ("share_to_feed", "true"),
        ("async_upload", "true"),
        ("request_id", request_id),
    ]
    if job.get("ia"):
        campos.append(("is_ai_generated", "true"))

    with open(video, "rb") as f:
        r = requests.post(
            f"{UPLOADPOST}/upload",
            headers={"Authorization": f"Apikey {chave}", "Idempotency-Key": request_id},
            data=campos,
            files={"video": (video.name, f, mimetypes.guess_type(video.name)[0] or "video/mp4")},
            timeout=600,
        )
    try:
        dados = r.json()
    except ValueError:
        dados = {"texto": r.text[:500]}
    if r.status_code == 429:
        erro(f"Acabaram os uploads grátis do mês no Upload-Post: {dados.get('usage')}")
    if r.status_code >= 300:
        erro(f"Upload-Post recusou ({r.status_code}): {dados}")

    if not dados.get("results"):
        for _ in range(150):
            time.sleep(10)
            s = requests.get(
                f"{UPLOADPOST}/uploadposts/status",
                headers={"Authorization": f"Apikey {chave}"},
                params={"request_id": dados.get("request_id") or request_id},
                timeout=30,
            )
            if s.status_code == 404:
                continue
            dados = s.json()
            log(f"{rede}: {dados.get('status')}")
            if dados.get("status") in ("completed", "failed"):
                break

    resultados = dados.get("results") or {}
    itens = resultados.values() if isinstance(resultados, dict) else resultados
    for item in itens:
        if item.get("skipped"):
            erro(f"{rede}: conta não conectada no Upload-Post.")
        if not item.get("success"):
            erro(f"{rede}: falhou: {item.get('message') or item.get('error')}")
        log(f"{rede} ok: {item.get('post_url') or item.get('url') or 'publicado'}")
    if dados.get("status") == "failed":
        erro(f"{rede}: falhou: {dados.get('message')}")


# ---------------------------------------------------------------- principal

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in REDES:
        erro("Uso: python postador/postar.py <youtube|instagram|tiktok> <pasta_do_job>")
    rede, pasta = sys.argv[1], Path(sys.argv[2])

    job = json.loads((pasta / "job.json").read_text(encoding="utf-8"))
    video = pasta / job.get("arquivo", "video.mp4")
    if not video.exists():
        erro(f"Vídeo não encontrado: {video}")

    log(f"Postando {video.name} ({video.stat().st_size / 1e6:.1f} MB) no {rede}")
    if rede == "instagram":
        if os.environ.get("IG_ACCESS_TOKEN", "").strip():
            postar_instagram(job, video)
        else:
            postar_uploadpost(rede, job, video)
    else:
        postar_darkpost(rede, job, video)


if __name__ == "__main__":
    main()
