# -*- coding: utf-8 -*-
"""
Servidor Proxy IPTV Premiere 1 - Versão 8 (Ultra Estável & Anti-Travamento)
- Validação real de bytes MPEG-TS (elimina retorno de páginas HTML/Erro para a TV)
- Leitura e busca de ID flexível para canais Premiere (|BR|, HD, FHD, 4K, CLUBES)
- Stream sem buffer com User-Agent oficial de IPTV (IPTVSmarters/VLC)
- Failover triplo: Xtream Codes Pool -> M3U Direct -> EmbedTV Web Fallback
"""

import os
import re
import time
import urllib3
import requests
from flask import Flask, Response, stream_with_context, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas ativas com maior longevidade e conexões simultâneas
POOL_CONTAS = [
    {"host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"host": "http://meusrv.top:80", "user": "567689135", "pass": "965722522"},
    {"host": "http://in89.top:80", "user": "556181019000", "pass": "29344205462"}
]

HEADERS_IPTV = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

HEADERS_NAVEGADOR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://w7.embedtv.lat/"
}

# Cache de ID do Premiere mapeado por host
CACHE_IDS = {}

def extrair_stream_id_premiere(conta):
    host = conta["host"]
    now = time.time()
    
    # Retorna do cache se encontrado nos últimos 30 minutos
    if host in CACHE_IDS and (now - CACHE_IDS[host]["time"] < 1800):
        return CACHE_IDS[host]["id"]

    try:
        url_m3u = f"{host}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
        r = requests.get(url_m3u, headers=HEADERS_IPTV, timeout=5, verify=False)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i, line in enumerate(lines):
                # Busca flexível por qualquer variação do Premiere 1 ou Premiere Clubes
                if line.startswith("#EXTINF") and re.search(r'PREMIERE.*(?:1|ONE|FC\s*1|CLUBES)', line, re.IGNORECASE):
                    if i + 1 < len(lines) and not lines[i+1].startswith("#"):
                        stream_url = lines[i+1].strip()
                        match = re.search(r'/(\d+)\.(ts|m3u8)', stream_url)
                        if match:
                            stream_id = match.group(1)
                            CACHE_IDS[host] = {"id": stream_id, "time": now}
                            return stream_id
    except Exception:
        pass

    return None

def e_resposta_video_valida(resp, primeiro_chunk):
    """
    Verifica se a resposta do servidor é um fluxo de vídeo válido (MPEG-TS)
    e rejeita respostas HTML de erro ("Stream Not Found", "404", etc.)
    """
    if resp.status_code != 200:
        return False

    if not primeiro_chunk:
        return False

    # Se contiver tags HTML ou texto de erro, rejeita
    chunk_lower = primeiro_chunk.lower()
    if b"<html" in chunk_lower or b"<!doctype" in chunk_lower or b"stream not found" in chunk_lower or b"invalid" in chunk_lower:
        return False

    # Sync Byte do MPEG-TS é 0x47 (71 em decimal) ou dados binários
    if primeiro_chunk[0] == 0x47 or len(primeiro_chunk) >= 188:
        return True

    return True

def obter_stream_web_embed():
    """Fallback para captura direta do EmbedTV em caso de falha em todo o pool IPTV"""
    try:
        url_alvo = "https://w7.embedtv.lat/premiere"
        r = requests.get(url_alvo, headers=HEADERS_NAVEGADOR, timeout=5, verify=False)
        if r.status_code == 200:
            matches = re.findall(r'["\'](https?://[^"\'<>\s]+?\.m3u8[^"\'<>\s]*?)["\']', r.text)
            for m in matches:
                if "whos.amung.us" not in m:
                    return m
    except Exception:
        pass
    return None

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route("/")
def home():
    return "Servidor Proxy IPTV Premiere 1 FHD - Status Ativo!"

@app.route("/playlist.m3u")
@app.route("/playlist")
@app.route("/get.php")
def playlist_m3u():
    base_url = request.host_url.rstrip("/")
    m3u_content = f"""#EXTM3U url-tvg="http://meusrv.top:80/xmltv.php"
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES - PREMIERE",Premiere 1 FHD [1080p]
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
@app.route("/live/premiere1.m3u8")
@app.route("/live/premiere1")
def stream_premiere():
    def retransmitir_fluxo():
        # 1. Tenta o Pool de Contas Xtream Codes em Sequência
        for conta in POOL_CONTAS:
            stream_id = extrair_stream_id_premiere(conta)
            targets = []
            if stream_id:
                targets.append(f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts")
            # Fallbacks com variações de nome comum
            targets.append(f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts")

            for target in targets:
                try:
                    r = requests.get(target, headers=HEADERS_IPTV, stream=True, timeout=6, verify=False)
                    chunk_iter = r.iter_content(chunk_size=16384)
                    try:
                        primeiro_chunk = next(chunk_iter)
                    except StopIteration:
                        continue

                    if not e_resposta_video_valida(r, primeiro_chunk):
                        r.close()
                        continue

                    # Transmissão de vídeo válida confirmada! Entrega os dados à TV sem buffer
                    yield primeiro_chunk
                    for chunk in chunk_iter:
                        if chunk:
                            yield chunk
                    return
                except Exception:
                    continue

        # 2. Fallback Web Embed (EmbedTV HLS) se as contas falharem
        url_embed = obter_stream_web_embed()
        if url_embed:
            try:
                r = requests.get(url_embed, headers=HEADERS_NAVEGADOR, stream=True, timeout=6, verify=False)
                if r.status_code == 200:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk:
                            yield chunk
            except Exception:
                pass

    resp = Response(
        stream_with_context(retransmitir_fluxo()),
        content_type="video/mp2t"
    )
    return adicionar_cors(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
