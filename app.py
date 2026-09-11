# -*- coding: utf-8 -*-
import os
import re
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# -------------------------------------------------------------------
# 1. SELEÇÃO DAS 5 FONTES PRINCIPAIS (ALTA CONECTIVIDADE E VALIDADE LONGA)
# -------------------------------------------------------------------
CONTAS_PRINCIPAIS = [
    # Fonte 1: meusrv.top (Usuário 955823677, expira em 2027, 3 conexões)
    {"nome": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634"},
    # Fonte 2: meusrv.top (Usuário 74468590, expira em 2027, 3 conexões)
    {"nome": "meusrv_2", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959"},
    # Fonte 3: 79.127.243.145 (Usuário 723015, expira no fim de 2026, 3 conexões)
    {"nome": "ono_1", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD"},
    # Fonte 4: assistirja.com (Usuário p2WzY2, expira em 2027)
    {"nome": "assistirja_1", "host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3"},
    # Fonte 5: assistirja.com (Usuário mqKTBr4T7N, expira em 2027, 2 conexões)
    {"nome": "assistirja_2", "host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp"}
]

# -------------------------------------------------------------------
# 2. FONTE RESERVA DE EMERGÊNCIA (USADA CASO AS 5 PRINCIPAIS FALHEM)
# -------------------------------------------------------------------
CONTA_RESERVA = {
    # Fonte Reserva: play.biturl.vip (Usuário 5181603291, expira em 2029)
    "nome": "biturl_reserva",
    "host": "http://play.biturl.vip:80",
    "user": "5181603291",
    "pass": "m23bm8a1nup"
}

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12",
    "Accept": "*/*"
}

def extrair_stream_id_premiere(host, user, password):
    """
    Baixa a M3U da conta específica e extrai o ID numérico do canal com o nome 'Premiere'.
    """
    try:
        url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS, timeout=5, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                # Procura por linhas do tipo #EXTINF que contenham PREMIERE
                if "PREMIERE 1" in linha.upper() or "PREMIERE FC 1" in linha.upper() or "PREMIERE HD" in linha.upper():
                    if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                        # Extrai o ID numérico do link (ex: /live/user/pass/12345.ts)
                        match = re.search(r'/(\d+)\.(ts|m3u8)', linhas[i+1])
                        if match:
                            return match.group(1)
    except Exception:
        pass
    return None

def e_fluxo_video_valido(chunk_inicial):
    """
    Verifica se os primeiros bytes contêm vídeo real e não respostas de erro HTML
    como 'Stream Not Found' ou '<html'.
    """
    if not chunk_inicial:
        return False
    # Se o início contiver tags HTML ou mensagens de erro em texto, não é vídeo
    amostra = chunk_inicial[:500].lower()
    if b"<html" in amostra or b"<!doctype" in amostra or b"stream not found" in amostra:
        return False
    return True

def tentar_transmitir_conta(conta):
    """
    Tenta obter o ID do Premiere na conta informada e retransmitir o fluxo de vídeo.
    """
    stream_id = extrair_stream_id_premiere(conta["host"], conta["user"], conta["pass"])
    if not stream_id:
        # Se não achou o ID numérico, tenta o apelido padrão 'premiere1'
        stream_id = "premiere1"

    stream_target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_id}.ts"
    
    try:
        req = requests.get(stream_target, headers=HEADERS, stream=True, timeout=6, verify=False)
        if req.status_code == 200:
            iterador = req.iter_content(chunk_size=16384)
            primeiro_chunk = next(iterador, None)
            
            # Valida se os primeiros bytes são de vídeo real
            if primeiro_chunk and e_fluxo_video_valido(primeiro_chunk):
                def gerador_stream():
                    yield primeiro_chunk
                    for chunk in iterador:
                        if chunk:
                            yield chunk
                return gerador_stream()
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
    return "Servidor Proxy IPTV - 5 Contas Principais + TXT Reserva Ativo!"

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
    # 1. TENTA CADA UMA DAS 5 FONTES PRINCIPAIS
    for conta in CONTAS_PRINCIPAIS:
        fluxo = tentar_transmitir_conta(conta)
        if fluxo:
            resp = Response(fluxo, content_type="video/mp2t")
            return adicionar_cors(resp)

    # 2. CASO NENHUMA DAS 5 FUNCIONE: USA A CONTA RESERVA DO TXT
    fluxo_reserva = tentar_transmitir_conta(CONTA_RESERVA)
    if fluxo_reserva:
        resp = Response(fluxo_reserva, content_type="video/mp2t")
        return adicionar_cors(resp)

    return "Todas as 5 contas principais e a fonte reserva estão indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
