# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas extraídas dos seus arquivos .txt
POOL_CONTAS = [
    {"nome": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"nome": "meusrv_2", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    {"nome": "ip103_1", "host": "http://103.176.90.186:80", "user": "e0828d9135", "pass": "e91802270546"},
    {"nome": "xyz332_1", "host": "http://332nr7hbfu.xyz:80", "user": "988060", "pass": "zd7YEw"},
    {"nome": "vector_1", "host": "http://61701-vector.cdn-o2.me:80", "user": "4df74cf07e", "pass": "9d49be6b44bc"},
    {"nome": "biturl_1", "host": "http://play.biturl.vip:80", "user": "5181603291", "pass": "m23bm8a1nup"}
]

HEADERS_PLAYER = {
    "User-Agent": "TiviMate/4.6.1 (Android TV)",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# Cache de ID do Premiere para não sobrecarregar o servidor
CACHE_PREMIERE = {"id_map": {}, "timestamp": 0}

def buscar_stream_id_real(host, user, password):
    """
    Busca o ID numérico exato do canal Premiere na playlist M3U da conta.
    Evita usar 'premiere1.ts' genérico que aciona o erro 404/Cloudflare.
    """
    try:
        url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS_PLAYER, timeout=5, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                if "PREMIERE 1" in linha.upper() or "PREMIERE FC 1" in linha.upper() or "PREMIERE HD" in linha.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        match = re.search(r'/(\d+)\.(ts|m3u8)', linhas[i+1])
                        if match:
                            return match.group(1)
    except Exception:
        pass
    return None

def obter_url_canal_valido():
    """
    Verifica qual servidor tem o canal ativo e retorna a URL direta.
    """
    for conta in POOL_CONTAS:
        stream_id = buscar_stream_id_real(conta["host"], conta["user"], conta["pass"])
        if not stream_id:
            continue
        
        target_url = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
        try:
            r = requests.head(target_url, headers=HEADERS_PLAYER, timeout=4, verify=False)
            if r.status_code == 200:
                return target_url
        except Exception:
            continue
    return None

@app.route("/")
def home():
    return "Servidor Proxy IPTV - Solução Burlar Cloudflare Ativa!"

@app.route("/playlist.m3u")
def playlist_m3u():
    base_url = request.host_url.rstrip("/")
    m3u_content = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def stream_premiere():
    # MÉTODO DE BYPASS: REDIRECIONAMENTO DIRETO (HTTP 302)
    # Em vez do Render tentar baixar (o que a Cloudflare bloqueia por ser IP de nuvem),
    # o Render envia a URL validada diretamente para a sua Smart TV abrir com o IP da sua casa.
    url_direta = obter_url_canal_valido()
    if url_direta:
        return redirect(url_direta, code=302)
    
    return "Nenhum servidor no pool respondeu com sinal válido.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
