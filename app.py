# -*- coding: utf-8 -*-
"""
Servidor Proxy IPTV - Versão v11 (Consumo Direto de stream_config.json)
Leitura ultra-rápida (0.01s) de mapa de canais organizado sem delays ou erros de raspagem na TV.
"""

import os
import json
import time
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

CONFIG_URL_RAW = "https://raw.githubusercontent.com/testes2601-collab/Servidor-Premiere/main/stream_config.json"
CACHE_CONFIG = {"dados": None, "timestamp": 0}

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def carregar_config_organizada():
    """
    Carrega o 'stream_config.json' da nuvem (GitHub Raw) ou arquivo local com cache de 5 minutos.
    """
    if CACHE_CONFIG["dados"] and (time.time() - CACHE_CONFIG["timestamp"] < 300):
        return CACHE_CONFIG["dados"]

    try:
        url_nocache = f"{CONFIG_URL_RAW}?t={int(time.time())}"
        r = requests.get(url_nocache, timeout=5)
        if r.status_code == 200:
            dados = r.json()
            if "canais" in dados:
                CACHE_CONFIG["dados"] = dados
                CACHE_CONFIG["timestamp"] = time.time()
                return dados
    except Exception:
        pass

    if os.path.exists("stream_config.json"):
        try:
            with open("stream_config.json", "r", encoding="utf-8") as f:
                dados = json.load(f)
                CACHE_CONFIG["dados"] = dados
                CACHE_CONFIG["timestamp"] = time.time()
                return dados
        except Exception:
            pass

    return {"canais": {}}

def e_video_valido(chunk_inicial):
    if not chunk_inicial:
        return False
    amostra = chunk_inicial[:500].lower()
    if b"<html" in amostra or b"<!doctype" in amostra or b"stream not found" in amostra:
        return False
    return True

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    config = carregar_config_organizada()
    qtd = len(config.get("canais", {}))
    return f"Servidor Proxy IPTV v11 - Online! ({qtd} canais catalogados e organizados no JSON)"

@app.route("/playlist.m3u")
def playlist_m3u():
    """
    Gera a playlist M3U enxuta contendo apenas os canais catalogados no 'stream_config.json'.
    """
    config = carregar_config_organizada()
    canais = config.get("canais", {})
    base_url = request.host_url.rstrip("/")

    linhas_m3u = ["#EXTM3U"]
    for slug, c in canais.items():
        tvg_id = c.get("tvg_id", "")
        nome = c.get("nome", slug)
        logo = c.get("logo", "")
        cat = c.get("categoria", "CANAIS")
        
        linha_inf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{nome}" tvg-logo="{logo}" group-title="{cat}",{nome}'
        linha_url = f'{base_url}/live/{slug}.ts'
        linhas_m3u.append(linha_inf)
        linhas_m3u.append(linha_url)

    conteudo_final = "\n".join(linhas_m3u)
    resp = Response(conteudo_final, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/<channel_slug>.ts")
@app.route("/live/<channel_slug>.m3u8")
def stream_canal(channel_slug):
    """
    Rota universal de canal: busca as fontes organizadas no JSON para o canal solicitado.
    """
    # Trata atalhos (ex: premiere1 ou premiere)
    slug_limpo = channel_slug.replace(".ts", "").replace(".m3u8", "")
    if slug_limpo == "premiere":
        slug_limpo = "premiere1"

    config = carregar_config_organizada()
    info_canal = config.get("canais", {}).get(slug_limpo)

    if not info_canal or not info_canal.get("fontes"):
        return f"Canal '{slug_limpo}' não encontrado ou sem fontes ativas no JSON.", 404

    fontes = info_canal["fontes"]

    # Testa as fontes em ordem de prioridade
    for fonte in fontes:
        host = fonte["host"]
        user = fonte["user"]
        password = fonte["pass"]
        sid = fonte["stream_id"]

        target_url = f"{host}/live/{user}/{password}/{sid}.ts"
        try:
            req = requests.get(target_url, headers=HEADERS, stream=True, timeout=5, verify=False)
            if req.status_code == 200:
                iterador = req.iter_content(chunk_size=16384)
                primeiro_chunk = next(iterador, None)

                if primeiro_chunk and e_video_valido(primeiro_chunk):
                    def gerador_stream():
                        yield primeiro_chunk
                        for chunk in iterador:
                            if chunk:
                                yield chunk
                    resp = Response(gerador_stream(), content_type="video/mp2t")
                    return adicionar_cors(resp)
        except Exception:
            continue

    return "Todas as fontes mapeadas para este canal estão indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
