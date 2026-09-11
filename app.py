# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# -------------------------------------------------------------------
# FONTES POR IP DIRETO (SEM DOMÍNIO / SEM CLOUDFLARE)
# Servidores com IP numérico direto nunca passam pelos bloqueios da Cloudflare
# -------------------------------------------------------------------
CONTAS_IP_DIRETO = [
    # Fonte 1: IP Direto (Usuário e0828d9135, expira em 2027)
    {"nome": "ip_103_a", "host": "http://103.176.90.186:80", "user": "e0828d9135", "pass": "e91802270546"},
    # Fonte 2: IP Direto (Usuário 7b559c1042, expira em 2026)
    {"nome": "ip_103_b", "host": "http://103.176.90.186:80", "user": "7b559c1042", "pass": "11de4cebb4"},
    # Fonte 3: IP Direto ONO (Usuário 723015, expira em 2026)
    {"nome": "ip_79_ono", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    # Fonte 4: Dyn IP ONO (Usuário Otaviodeledove)
    {"nome": "ip_85_ono", "host": "http://85.137.49.157.dyn.user.ono.com:80", "user": "Otaviodeledove", "pass": "9Dh5R8uAu5"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def obter_url_real_premiere(conta):
    """
    Baixa a lista M3U oficial da conta via IP direto e localiza o ID numérico exato do Premiere.
    """
    try:
        url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS, timeout=6, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                if "PREMIERE 1" in linha.upper() or "PREMIERE FC 1" in linha.upper() or "PREMIERE HD" in linha.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        link_stream = linhas[i+1].strip()
                        if link_stream.startswith("http"):
                            return link_stream
                        else:
                            return f"{conta['host']}{link_stream}"
    except Exception:
        pass
    
    # Se não conseguir a M3U, retorna a rota padrão
    return f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

@app.route("/")
def home():
    return "Servidor Proxy Premiere 1 - Modo IP Direto (Sem Cloudflare) OK!"

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
    # Testa apenas servidores com IP numérico direto (livres de Cloudflare)
    for conta in CONTAS_IP_DIRETO:
        url_canal = obter_url_real_premiere(conta)
        try:
            r = requests.head(url_canal, headers=HEADERS, timeout=4, verify=False)
            if r.status_code in [200, 302]:
                # Redireciona a TV diretamente para o IP bruto do servidor sem passar pela Cloudflare
                return redirect(url_canal, code=302)
        except Exception:
            continue

    return "Nenhum servidor de IP direto respondeu para o Premiere no momento.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
