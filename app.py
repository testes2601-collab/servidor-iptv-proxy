# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

POOL_CONTAS = [
    {"host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"host": "http://meusrv.top:80", "user": "567689135", "pass": "965722522"},
    {"host": "http://in89.top:80", "user": "556181019000", "pass": "29344205462"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route("/")
def home():
    return "Servidor Proxy IPTV Estável - Online!"

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
def stream_premiere():
    def gerar_fluxo_continuo():
        for conta in POOL_CONTAS:
            try:
                # 1. Busca a playlist para identificar o ID numérico do canal
                url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
                r_m3u = requests.get(url_m3u, headers=HEADERS, timeout=6, verify=False)
                
                stream_id = None
                if r_m3u.status_code == 200:
                    lines = r_m3u.text.splitlines()
                    for i, line in enumerate(lines):
                        if "PREMIERE 1" in line.upper() or "PREMIERE FC 1" in line.upper():
                            if i + 1 < len(lines) and not lines[i+1].startswith("#"):
                                match = re.search(r'/live/[^/]+/[^/]+/(\d+)\.ts', lines[i+1])
                                if match:
                                    stream_id = match.group(1)
                                    break
                
                if not stream_id:
                    continue

                # 2. Conecta no stream direto com suporte a streaming contínuo
                target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
                with requests.get(target, headers=HEADERS, stream=True, timeout=10, verify=False) as req:
                    if req.status_code == 200:
                        for chunk in req.iter_content(chunk_size=65536):
                            if chunk:
                                yield chunk
            except Exception:
                continue

    resp = Response(gerar_fluxo_continuo(), content_type="video/mp2t")
    return adicionar_cors(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
