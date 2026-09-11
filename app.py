# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool exclusivo contendo APENAS as suas contas M3U / Xtream oficiais
POOL_CONTAS = [
    {"nome": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"nome": "meusrv_2", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"nome": "assistirja_1", "host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
    {"nome": "assistirja_2", "host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Proxy Premiere 1 FHD - Exclusivo das Listas M3U!"

@app.route("/debug")
def debug():
    """
    Rota de diagnóstico para checar a saúde das 5 contas do seu pool das listas M3U.
    """
    relatorio = ["<h2>Diagnóstico de Saúde do Pool M3U (Premiere 1)</h2>"]
    
    for conta in POOL_CONTAS:
        try:
            url_test = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
            r = requests.head(url_test, headers=HEADERS, timeout=4, verify=False)
            status = f"<span style='color:green;'>ONLINE (HTTP {r.status_code})</span>" if r.status_code == 200 else f"<span style='color:orange;'>RESPOSTA HTTP {r.status_code}</span>"
            relatorio.append(f"<b>{conta['nome']}</b> ({conta['host']}): {status}<br>")
        except Exception as e:
            relatorio.append(f"<b>{conta['nome']}</b> ({conta['host']}): <span style='color:red;'>OFFLINE ({e})</span><br>")
            
    return "".join(relatorio)

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
    # Testa em sequência apenas as contas M3U oficiais
    for conta in POOL_CONTAS:
        target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        try:
            req = requests.get(target_url, headers=HEADERS, stream=True, timeout=5, verify=False)
            if req.status_code == 200:
                iterador = req.iter_content(chunk_size=32768)
                primeiro_chunk = next(iterador, None)
                
                # Valida se é transmissão MPEG-TS de verdade e não página de erro HTML
                if primeiro_chunk and not (b"<html" in primeiro_chunk.lower() or b"stream not found" in primeiro_chunk.lower()):
                    def gerador():
                        yield primeiro_chunk
                        for chunk in iterador:
                            if chunk:
                                yield chunk
                    resp = Response(gerador(), content_type="video/mp2t")
                    return adicionar_cors(resp)
        except Exception:
            continue

    return "Todas as 5 contas M3U do Premiere estão indisponíveis no momento.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
