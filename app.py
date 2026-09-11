# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool expandido de contas M3U de alta estabilidade
POOL_CONTAS = [
    {"nome": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"nome": "meusrv_2", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"nome": "assistirja_1", "host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
    {"nome": "assistirja_2", "host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"},
    {"nome": "in89_1", "host": "http://in89.top:80", "user": "556181019000", "pass": "29344205462"},
    {"nome": "biturl_reserva", "host": "http://play.biturl.vip:80", "user": "5181603291", "pass": "m23bm8a1nup"}
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
    return "Servidor Proxy Premiere 1 - Exclusivo das Listas M3U (Filtro Anti-Cloudflare Ativo)!"

@app.route("/debug")
def debug():
    """
    Painel de diagnóstico em português sobre a saúde das contas do pool.
    """
    relatorio = [
        "<h2>Diagnóstico de Saúde do Pool M3U (Premiere 1)</h2>",
        "<p>Verificação de status e detecção de bloqueios em tempo real:</p><hr>"
    ]
    
    for conta in POOL_CONTAS:
        try:
            url_test = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
            r = requests.get(url_test, headers=HEADERS, stream=True, timeout=4, verify=False)
            if r.status_code == 200:
                primeiro_bloco = next(r.iter_content(chunk_size=4096), b"")
                amostra = primeiro_bloco.lower()
                if b"cloudflare" in amostra or b"restricted" in amostra:
                    status = "<span style='color:red;'>BLOQUEADO PELA CLOUDFLARE (Rejeitado)</span>"
                elif b"<html" in amostra or b"stream not found" in amostra:
                    status = "<span style='color:orange;'>ERRO HTML / CANAL INDISPONÍVEL</span>"
                else:
                    status = "<span style='color:green;'>ONLINE (Vídeo Real OK)</span>"
            else:
                status = f"<span style='color:orange;'>HTTP {r.status_code}</span>"
            relatorio.append(f"<b>{conta['nome']}</b> ({conta['host']}): {status}<br>")
        except Exception as e:
            relatorio.append(f"<b>{conta['nome']}</b> ({conta['host']}): <span style='color:red;'>OFFLINE</span><br>")
            
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

def validar_e_transmitir(target_url):
    try:
        req = requests.get(target_url, headers=HEADERS, stream=True, timeout=5, verify=False)
        if req.status_code == 200:
            iterador = req.iter_content(chunk_size=32768)
            primeiro_chunk = next(iterador, None)
            
            if primeiro_chunk:
                amostra = primeiro_chunk.lower()
                # Descarta se contiver tela de erro da Cloudflare ou páginas HTML
                if b"cloudflare" in amostra or b"restricted" in amostra or b"<html" in amostra or b"stream not found" in amostra:
                    return None
                
                def gerador():
                    yield primeiro_chunk
                    for chunk in iterador:
                        if chunk:
                            yield chunk
                return gerador()
    except Exception:
        pass
    return None

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def stream_premiere():
    # Testa em sequência o pool de contas M3U descartando bloqueios automaticamente
    for conta in POOL_CONTAS:
        # Tenta a rota direta do Premiere 1
        url_direta = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        fluxo = validar_e_transmitir(url_direta)
        if fluxo:
            resp = Response(fluxo, content_type="video/mp2t")
            return adicionar_cors(resp)
            
    return "Todas as contas M3U do Premiere estão temporariamente indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
