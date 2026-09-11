# -*- coding: utf-8 -*-
import os
import re
import time
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas de alta estabilidade
POOL_CONTAS = [
    {"host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"host": "http://meusrv.top:80", "user": "567689135", "pass": "965722522"},
    {"host": "http://in89.top:80", "user": "556181019000", "pass": "29344205462"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

# Cache do ID do Premiere para não travar a abertura na TV
CACHE_STREAM = {"id": None, "timestamp": 0}

def obter_stream_id_premiere():
    # Se o ID já foi localizado há menos de 1 hora, usa o cache instantâneo
    if CACHE_STREAM["id"] and (time.time() - CACHE_STREAM["timestamp"] < 3600):
        return CACHE_STREAM["id"]

    for conta in POOL_CONTAS:
        try:
            url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
            r = requests.get(url_m3u, headers=HEADERS, timeout=5, verify=False)
            if r.status_code == 200:
                lines = r.text.splitlines()
                for i, line in enumerate(lines):
                    if "PREMIERE 1" in line.upper() or "PREMIERE FC 1" in line.upper():
                        if i + 1 < len(lines) and not lines[i+1].startswith("#"):
                            match = re.search(r'/(\d+)\.(ts|m3u8)', lines[i+1])
                            if match:
                                stream_id = match.group(1)
                                CACHE_STREAM["id"] = stream_id
                                CACHE_STREAM["timestamp"] = time.time()
                                return stream_id
        except Exception:
            continue
    return None

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Proxy Premiere FHD - Status OK!"

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
    stream_id = obter_stream_id_premiere()
    
    # Testa as contas do pool para entregar a URL direta ativa
    for conta in POOL_CONTAS:
        try:
            if stream_id:
                target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
            else:
                target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"

            # Valida rapidamente se a conta responde
            check = requests.head(target_url, headers=HEADERS, timeout=3, verify=False)
            if check.status_code in [1, 2]:
                return redirect(target_url, code=302)
        except Exception:
            continue

    # Fallback direto na conta principal
    c = POOL_CONTAS
    sid = stream_id if stream_id else "premiere1"
    return redirect(f"{c['host']}/live/{c['user']}/{c['pass']}/{sid}.ts", code=302)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
