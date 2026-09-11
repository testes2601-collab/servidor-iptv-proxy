# -*- coding: utf-8 -*-
import os
import re
import json
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# User-Agent oficial de Smart TVs e Players IPTV para evitar bloqueio por bot
HEADERS_IPTV = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def carregar_config():
    """Carrega as fontes exclusivas do Premiere 1 a partir do stream_config.json."""
    try:
        if os.path.exists("stream_config.json"):
            with open("stream_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Estrutura padrão de emergência focada exclusivamente no Premiere 1
    return {
        "premiere1": {
            "nome": "Premiere 1 FHD",
            "fontes": [
                {"host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
                {"host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
                {"host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
                {"host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
                {"host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"}
            ],
            "reserva": {"host": "http://play.biturl.vip:80", "user": "5181603291", "pass": "m23bm8a1nup"}
        }
    }

def obter_stream_id_premiere(host, user, password):
    """Busca o ID numérico real do Premiere 1 na conta."""
    try:
        url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS_IPTV, timeout=4, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                if "PREMIERE 1" in linha.upper() or "PREMIERE FC 1" in linha.upper() or "PREMIERE HD" in linha.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        match = re.search(r'/(\d+)\.(ts|m3u8)', lines[i+1])
                        if match:
                            return match.group(1)
    except Exception:
        pass
    return None

def e_fluxo_video_valido(chunk):
    """Garante que a resposta é vídeo real e elimina mensagens HTML / Cloudflare."""
    if not chunk:
        return False
    amostra = chunk[:500].lower()
    # Filtra erros de Cloudflare TOS e páginas HTML de erro de servidor
    if b"cloudflare" in amostra or b"<html" in amostra or b"<!doctype" in amostra or b"stream not found" in amostra:
        return False
    return True

def tentar_stream_direto(host, user, password):
    """Conecta no servidor Xtream diretamente e retransmite o fluxo de vídeo."""
    stream_id = obter_stream_id_premiere(host, user, password)
    sid = stream_id if stream_id else "premiere1"
    target = f"{host}/live/{user}/{password}/{sid}.ts"

    try:
        req = requests.get(target, headers=HEADERS_IPTV, stream=True, timeout=6, verify=False)
        if req.status_code == 200:
            iterador = req.iter_content(chunk_size=32768)
            primeiro_chunk = next(iterador, None)

            if primeiro_chunk and e_fluxo_video_valido(primeiro_chunk):
                def gerador():
                    yield primeiro_chunk
                    for chunk in iterador:
                        if chunk:
                            yield chunk
                return gerador()
    except Exception:
        pass
    return None

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Exclusivo Premiere 1 FHD - Status OK!"

@app.route("/playlist.m3u")
def playlist_m3u():
    """Playlist contendo EXCLUSIVAMENTE o canal Premiere 1."""
    base_url = request.host_url.rstrip("/")
    m3u_content = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def stream_premiere():
    config = carregar_config()
    dados_p1 = config.get("premiere1", {})
    fontes = dados_p1.get("fontes", [])
    reserva = dados_p1.get("reserva", {})

    # 1. Testa em sequência as 5 contas principais diretas
    for fonte in fontes:
        fluxo = tentar_stream_direto(fonte["host"], fonte["user"], fonte["pass"])
        if fluxo:
            resp = Response(fluxo, content_type="video/mp2t")
            return adicionar_cors(resp)

    # 2. Se as 5 falharem, aciona a conta reserva direta
    if reserva:
        fluxo_res = tentar_stream_direto(reserva["host"], reserva["user"], reserva["pass"])
        if fluxo_res:
            resp = Response(fluxo_res, content_type="video/mp2t")
            return adicionar_cors(resp)

    return "Todas as fontes do Premiere 1 estão indisponíveis no momento.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
