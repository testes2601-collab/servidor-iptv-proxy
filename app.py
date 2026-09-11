# -*- coding: utf-8 -*-
import os
import re
import json
import time
import base64
import urllib3
import requests
from flask import Flask, Response, request

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

HEADERS_PADRAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

CACHE_STREAM = {"id": None, "timestamp": 0}

def obter_stream_id_premiere():
    if CACHE_STREAM["id"] and (time.time() - CACHE_STREAM["timestamp"] < 3600):
        return CACHE_STREAM["id"]

    for conta in POOL_CONTAS:
        try:
            url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
            r = requests.get(url_m3u, headers=HEADERS_PADRAO, timeout=6, verify=False)
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
    return "premiere1"

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Proxy IPTV HLS - Online!"

@app.route("/playlist.m3u")
def playlist_m3u():
    base_url = request.host_url.rstrip("/")
    m3u_content = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{base_url}/live/premiere1.m3u8
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.m3u8")
@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def play_m3u8():
    stream_id = obter_stream_id_premiere()
    
    for conta in POOL_CONTAS:
        # Tenta abrir o manifesto .m3u8 da fonte
        stream_target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.m3u8"
        try:
            r = requests.get(stream_target, headers=HEADERS_PADRAO, timeout=6, verify=False)
            if r.status_code == 200 and "#EXTM3U" in r.text:
                url_base = stream_target.rsplit('/', 1)[0] + '/'
                linhas = r.text.splitlines()
                m3u8_reescrito = []
                
                for linha in linhas:
                    linha = linha.strip()
                    if not linha:
                        continue
                    if linha.startswith("#"):
                        m3u8_reescrito.append(linha)
                    else:
                        url_seg_real = linha if linha.startswith("http") else url_base + linha
                        url_enc = base64.b64encode(url_seg_real.encode("utf-8")).decode("utf-8")
                        url_proxy = f"{request.url_root}segmento?data={url_enc}"
                        m3u8_reescrito.append(url_proxy)
                        
                conteudo_final = "\n".join(m3u8_reescrito)
                resp = Response(conteudo_final, content_type="application/x-mpegURL")
                return adicionar_cors(resp)
        except Exception:
            continue

    # Fallback TS direto
    for conta in POOL_CONTAS:
        stream_target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
        try:
            r = requests.get(stream_target, headers=HEADERS_PADRAO, stream=True, timeout=6, verify=False)
            if r.status_code == 200:
                def retransmitir():
                    for chunk in r.iter_content(chunk_size=32768):
                        if chunk:
                            yield chunk
                resp = Response(retransmitir(), content_type="video/mp2t")
                return adicionar_cors(resp)
        except Exception:
            continue

    return "Sinal temporariamente indisponível no pool.", 503

@app.route("/segmento")
def play_segmento():
    data_codificada = request.args.get("data")
    if not data_codificada:
        return "Dados ausentes", 400
    try:
        url_real = base64.b64decode(data_codificada).decode("utf-8")
        r = requests.get(url_real, headers=HEADERS_PADRAO, stream=True, timeout=10, verify=False)
        def retransmitir():
            for chunk in r.iter_content(chunk_size=32768):
                if chunk:
                    yield chunk
        resp = Response(retransmitir(), content_type=r.headers.get("Content-Type", "video/mp2t"))
        return adicionar_cors(resp)
    except Exception as e:
        return f"Erro no segmento: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
