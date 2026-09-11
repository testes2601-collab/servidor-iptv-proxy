# -*- coding: utf-8 -*-
"""
Servidor Proxy IPTV - Teste com Sinal Único (Premiere 1 - Qualidade Máxima FHD)
Suporte a Failover Automático com Pool de Contas de Alta Estabilidade
"""

import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas de elite para rodízio e failover
POOL_CONTAS = [
    {
        "host": "http://79.127.243.145:80",
        "user": "723015",
        "pass": "VfGrmD",
        "max_con": 3
    },
    {
        "host": "http://meusrv.top:80",
        "user": "171769357",
        "pass": "782164797",
        "max_con": 3
    },
    {
        "host": "http://meusrv.top:80",
        "user": "74468590",
        "pass": "448420959",
        "max_con": 3
    },
    {
        "host": "http://horizonmult.sbs:80",
        "user": "cmiz0qsdn001",
        "pass": "35998974504",
        "max_con": 2
    },
    {
        "host": "http://play.biturl.vip:80",
        "user": "5181603291",
        "pass": "m23bm8a1nup",
        "max_con": 1
    }
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
    return "Servidor Proxy Premiere FHD (Sinal Único de Alta Qualidade) Ativo!"

@app.route("/playlist.m3u")
def playlist_m3u():
    """
    Gera uma playlist M3U enxuta contendo unicamente o canal Premiere 1 FHD
    em altíssima definição, apontando a transmissão para o nosso proxy local.
    """
    base_url = request.host_url.rstrip("/")
    
    # Playlist focada exclusivamente no Premiere 1 em Qualidade Máxima (FHD / 1080p)
    m3u_content = f"""#EXTM3U url-tvg="http://meusrv.top:80/xmltv.php"
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES - PREMIERE",Premiere 1 FHD [1080p / 60FPS]
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.ts")
def stream_premiere():
    """
    Sintoniza e retransmite o sinal do Premiere 1 tentando as contas do pool em sequência.
    Se a Conta 1 oscilar ou atingir o limite, pula transparente para a próxima conta.
    """
    for idx, conta in enumerate(POOL_CONTAS, 1):
        # Tenta buscar a transmissão do Premiere 1 em formato TS / M3U8
        stream_target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        
        try:
            req = requests.get(stream_target, headers=HEADERS, stream=True, timeout=8, verify=False)
            if req.status_code == 200:
                def retransmitir():
                    for chunk in req.iter_content(chunk_size=32768):
                        yield chunk
                
                resp = Response(retransmitir(), content_type="video/mp2t")
                return adicionar_cors(resp)
        except Exception:
            # Em caso de falha de conexão, pula para a próxima conta do pool
            continue
            
    return "Todas as fontes do pool do Premiere estão temporariamente indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
