# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de Servidores M3U com os servidores HTTP 200 confirmados no topo
POOL_CONTAS = [
    # Servidores com retorno HTTP 200 direto e funcional (sem redirecionamentos 302 para Cloudflare)
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"nome": "vector_1", "host": "http://61701-vector.cdn-o2.me:80", "user": "4df74cf07e", "pass": "9d49be6b44bc"},
    {"nome": "ip103_1", "host": "http://103.176.90.186:80", "user": "e0828d9135", "pass": "e91802270546"},
    {"nome": "xyz332_1", "host": "http://332nr7hbfu.xyz:80", "user": "bf99kmWd", "pass": "sGqE59"},
    {"nome": "xyz332_2", "host": "http://332nr7hbfu.xyz:80", "user": "constancio79", "pass": "Wagner@79"},
    {"nome": "given_1", "host": "http://11359-given.cdn-o2.me:80", "user": "4af01daf4f", "pass": "7e3498490571"},
    {"nome": "fftq_1", "host": "http://49fftq.live:80", "user": "WellgtonSilva35", "pass": "991DNEubv"},
    {"nome": "z2mu_1", "host": "http://54z2mu.pro:80", "user": "jT63beuY", "pass": "F11Gkd"},
    {"nome": "horizon_1", "host": "http://horizonmult.sbs:80", "user": "cmguxxz8y001", "pass": "51993101526"},
    {"nome": "ono_2", "host": "http://85.137.49.157.dyn.user.ono.com:80", "user": "Otaviodeledove", "pass": "9Dh5R8uAu5"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

CACHE_STREAM = {}

def obter_stream_id_premiere(host, user, password):
    cache_key = f"{host}_{user}"
    if cache_key in CACHE_STREAM:
        return CACHE_STREAM[cache_key]

    try:
        url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS, timeout=4, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                if "PREMIERE 1" in linha.upper() or "PREMIERE FC 1" in linha.upper() or "PREMIERE HD" in linha.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        match = re.search(r'/(\d+)\.(ts|m3u8)', linhas[i+1])
                        if match:
                            sid = match.group(1)
                            CACHE_STREAM[cache_key] = sid
                            return sid
    except Exception:
        pass
    return "premiere1"

def e_fluxo_video_valido(chunk):
    if not chunk:
        return False
    amostra = chunk[:1000].lower()
    # Filtro rigoroso anti-Cloudflare e anti-HTML
    bloqueios = [
        b"cloudflare", b"cfl.re", b"restricted", b"terms of service",
        b"<html", b"<!doctype", b"stream not found", b"access denied", b"error"
    ]
    for b in bloqueios:
        if b in amostra:
            return False
    return True

def tentar_transmitir_conta(conta):
    stream_id = obter_stream_id_premiere(conta["host"], conta["user"], conta["pass"])
    target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
    
    try:
        req = requests.get(target_url, headers=HEADERS, stream=True, timeout=5, verify=False)
        
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
    return "Servidor Proxy Premiere 1 - Pool Filtrado v16 Online!"

@app.route("/debug")
def debug():
    relatorio = ["<h2>Status dos Servidores M3U (v16)</h2>"]
    for conta in POOL_CONTAS:
        try:
            sid = obter_stream_id_premiere(conta["host"], conta["user"], conta["pass"])
            url_test = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{sid}.ts"
            r = requests.get(url_test, headers=HEADERS, stream=True, timeout=4, verify=False)
            
            chunk = next(r.iter_content(chunk_size=1024), None)
            if r.status_code == 200 and e_fluxo_video_valido(chunk):
                status = f"<b style='color:green;'>ONLINE - VÍDEO OK (HTTP 200)</b>"
            elif r.status_code == 302:
                status = f"<b style='color:orange;'>REDIRECIONAMENTO (HTTP 302 - Ignorado)</b>"
            else:
                status = f"<b style='color:red;'>BLOQUEADO / CLOUDFLARE (HTTP {r.status_code})</b>"
            
            relatorio.append(f"• <b>{conta['nome']}</b> ({conta['host']}): {status}<br>")
        except Exception as e:
            relatorio.append(f"• <b>{conta['nome']}</b> ({conta['host']}): <b style='color:gray;'>OFFLINE ({e})</b><br>")
            
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
    for conta in POOL_CONTAS:
        fluxo = tentar_transmitir_conta(conta)
        if fluxo:
            resp = Response(fluxo, content_type="video/mp2t")
            return adicionar_cors(resp)

    return "Todos os servidores M3U estão temporariamente indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
