# -*- coding: utf-8 -*-
import os
import time
import json
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de Elite com as contas de maior longevidade (Validade 2027)
POOL_ELITE = [
    {"host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
    {"host": "http://assistirja.com:80", "user": "claudio0082x", "pass": "55052178"},
    {"host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"host": "http://meusrv.top:80", "user": "567689135", "pass": "965722522"},
    {"host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12"
}

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Proxy IPTV Automatizado - Status OK!"

@app.route("/playlist.m3u")
def playlist_m3u():
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
    # Testa em sequência o pool de elite com contas válidas até 2027
    for conta in POOL_ELITE:
        target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        try:
            r = requests.get(target_url, headers=HEADERS, stream=True, timeout=5, verify=False)
            if r.status_code == 200:
                # Transmite os blocos de vídeo diretamente em HTTPS sem passar por arquivo estático
                def retransmitir():
                    for chunk in r.iter_content(chunk_size=32768):
                        if chunk:
                            yield chunk
                resp = Response(retransmitir(), content_type="video/mp2t")
                return adicionar_cors(resp)
        except Exception:
            continue

    return "Todas as fontes do pool estão indisponíveis no momento.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
