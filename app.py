# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool Amplo e Diversificado de Contas extraídas de TODOS os arquivos .txt do projeto
POOL_CONTAS_DIVERSIFICADO = [
    # Server 1: meusrv.top
    {"nome": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    {"nome": "meusrv_2", "host": "http://meusrv.top:80", "user": "567689135", "pass": "965722522"},
    {"nome": "meusrv_3", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    # Server 2: assistirja.com
    {"nome": "assistirja_1", "host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
    {"nome": "assistirja_2", "host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"},
    {"nome": "assistirja_3", "host": "http://assistirja.com:80", "user": "claudio0082x", "pass": "55052178"},
    # Server 3: 79.127.243.145
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    # Server 4: 103.176.90.186
    {"nome": "ip103_1", "host": "http://103.176.90.186:80", "user": "e0828d9135", "pass": "e91802270546"},
    # Server 5: 61701-vector.cdn-o2.me
    {"nome": "vector_1", "host": "http://61701-vector.cdn-o2.me:80", "user": "f5b51b97c6", "pass": "0svwmrhvnj"},
    # Server 6: 654638.xyz
    {"nome": "xyz654_1", "host": "http://654638.xyz:80", "user": "MAGNFPGZY1", "pass": "adhus0TkBW"},
    # Server 7: 332nr7hbfu.xyz
    {"nome": "xyz332_1", "host": "http://332nr7hbfu.xyz:80", "user": "bf99kmWd", "pass": "sGqE59"},
    # Server 8: 966gaddn.com
    {"nome": "gaddn_1", "host": "http://966gaddn.com:80", "user": "5FA57F9827964FF", "pass": "irn2ylrD61"},
    # Server 9: play.biturl.vip
    {"nome": "biturl_1", "host": "http://play.biturl.vip:80", "user": "5181603291", "pass": "m23bm8a1nup"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def extrair_stream_id(host, user, password, termo="PREMIERE"):
    try:
        url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
        r = requests.get(url_m3u, headers=HEADERS, timeout=4, verify=False)
        if r.status_code == 200 and "#EXTM3U" in r.text:
            linhas = r.text.splitlines()
            for i, l in enumerate(linhas):
                if termo in l.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        m = re.search(r'/(\d+)\.(ts|m3u8)', linhas[i+1])
                        if m:
                            return m.group(1)
    except Exception:
        pass
    return None

def e_chunk_valido_sem_cloudflare(chunk):
    if not chunk or len(chunk) < 50:
        return False
    amostra = chunk[:1000].lower()
    # Verifica assinaturas de erro da Cloudflare ou páginas HTML
    bloqueios = [b"cloudflare", b"restricted", b"cfl.re", b"<html", b"<!doctype", b"stream not found", b"access denied"]
    for b in bloqueios:
        if b in amostra:
            return False
    return True

def adicionar_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp

@app.route("/")
def home():
    return "Servidor Proxy IPTV - Premiere 1 FHD (Pool Expandido Multi-Servidores)"

@app.route("/playlist.m3u")
def playlist():
    base = request.host_url.rstrip("/")
    m3u = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{base}/live/premiere1.ts
"""
    return adicionar_cors(Response(m3u, content_type="application/x-mpegURL"))

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def stream():
    for c in POOL_CONTAS_DIVERSIFICADO:
        stream_id = extrair_stream_id(c["host"], c["user"], c["pass"], "PREMIERE")
        target_id = stream_id if stream_id else "premiere1"
        url = f"{c['host']}/live/{c['user']}/{c['pass']}/{target_id}.ts"
        
        try:
            req = requests.get(url, headers=HEADERS, stream=True, timeout=5, verify=False)
            if req.status_code == 200:
                it = req.iter_content(chunk_size=32768)
                p_chunk = next(it, None)
                if e_chunk_valido_sem_cloudflare(p_chunk):
                    def gerador():
                        yield p_chunk
                        for chunk in it:
                            if chunk:
                                yield chunk
                    return adicionar_cors(Response(gerador(), content_type="video/mp2t"))
        except Exception:
            continue
            
    return "Nenhum servidor do pool entregou sinal limpo no momento.", 503

@app.route("/debug")
def debug():
    html = ["<h2>Status em Tempo Real do Pool de Servidores M3U</h2><hr>"]
    for c in POOL_CONTAS_DIVERSIFICADO:
        try:
            url = f"{c['host']}/live/{c['user']}/{c['pass']}/premiere1.ts"
            r = requests.head(url, headers=HEADERS, timeout=3, verify=False)
            status = f"<b style='color:green;'>ONLINE (HTTP {r.status_code})</b>" if r.status_code == 200 else f"<b style='color:orange;'>HTTP {r.status_code}</b>"
        except Exception as e:
            status = f"<b style='color:red;'>OFFLINE ({e})</b>"
        html.append(f"<p>Servidor <b>{c['nome']}</b> ({c['host']}): {status}</p>")
    return "".join(html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
