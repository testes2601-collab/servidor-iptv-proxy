# -*- coding: utf-8 -*-
"""
Servidor Proxy IPTV - Versão Unificada de Alta Compatibilidade (FHD)
Suporta múltiplos endpoints (/playlist.m3u, /playlist, /get.php, /debug, /live/*)
e inclui tratamento de rotas não encontradas para evitar erros 404.
"""

import os
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas de alta estabilidade para o Premiere 1
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
    base = request.host_url.rstrip("/")
    html = f"""
    <h2>Servidor Proxy IPTV Ativo!</h2>
    <p><b>Links de Acesso Rápidos:</b></p>
    <ul>
        <li><b>Lista M3U Completa:</b> <a href="{base}/playlist.m3u">{base}/playlist.m3u</a></li>
        <li><b>Sinal Direto Premiere 1 FHD:</b> <a href="{base}/live/premiere1.ts">{base}/live/premiere1.ts</a></li>
        <li><b>Painel de Diagnóstico:</b> <a href="{base}/debug">{base}/debug</a></li>
    </ul>
    """
    resp = Response(html, content_type="text/html; charset=utf-8")
    return adicionar_cors(resp)

@app.route("/playlist.m3u")
@app.route("/playlist")
@app.route("/playlist.m3u8")
@app.route("/get.php")
def playlist_m3u():
    """
    Gera a playlist M3U universal compatível com qualquer player de TV.
    """
    base_url = request.host_url.rstrip("/")
    m3u_content = f"""#EXTM3U url-tvg="http://meusrv.top:80/xmltv.php"
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES - PREMIERE",Premiere 1 FHD [1080p / 60FPS]
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
@app.route("/live/premiere1")
@app.route("/live/premiere")
def stream_premiere():
    """
    Sintoniza e retransmite o sinal do Premiere 1 usando o pool de contas com failover automático.
    """
    for conta in POOL_CONTAS:
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
            continue
            
    return "Todas as fontes do pool estão indisponíveis no momento.", 503

@app.route("/debug")
def debug():
    """
    Painel de diagnóstico de saúde do pool de contas.
    """
    status_list = []
    for idx, conta in enumerate(POOL_CONTAS, 1):
        test_url = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
        try:
            r = requests.head(test_url, headers=HEADERS, timeout=4, verify=False)
            st = f"ONLINE (HTTP {r.status_code})" if r.status_code == 200 else f"ALERTA (HTTP {r.status_code})"
        except Exception as e:
            st = f"OFFLINE ({e})"
        status_list.append(f"<b>Conta {idx} ({conta['host']}):</b> {st}")
    
    html = f"<h3>Status de Saúde do Pool de Fontes:</h3><br>" + "<br>".join(status_list)
    resp = Response(html, content_type="text/html; charset=utf-8")
    return adicionar_cors(resp)

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    """
    Redireciona qualquer rota inválida ou não mapeada diretamente para a página inicial.
    """
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
