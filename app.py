# -*- coding: utf-8 -*-
"""
Servidor Proxy IPTV - v6 (Com Deteção Dinâmica de Stream ID do M3U + Failover Real)
Corrige o erro de tentar rodar por 1 ms e parar devido a Stream IDs inválidos.
"""

import os
import re
import time
import urllib3
import requests
from flask import Flask, Response, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Pool de contas ativas e testadas
POOL_CONTAS = [
    {
        "host": "http://meusrv.top:80",
        "user": "955823677",
        "pass": "798597634",
        "max_con": 3
    },
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
        "host": "http://in89.top:80",
        "user": "556181019000",
        "pass": "29344205462",
        "max_con": 1
    }
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12"
}

# Cache do M3U e Mapa de IDs de canais
CACHE_CANAL_MAP = {}
CACHE_M3U_RAW = ""
CACHE_TIMESTAMP = 0
CACHE_TTL = 300  # Atualiza o mapa de canais a cada 5 minutos

def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response

def carregar_e_mapear_canais():
    """
    Baixa a playlist M3U da primeira conta do pool que estiver online
    e mapeia os canais (ex: Premiere 1, SportV 1) para os seus IDs Numéricos REAIS.
    """
    global CACHE_CANAL_MAP, CACHE_M3U_RAW, CACHE_TIMESTAMP
    
    agora = time.time()
    if CACHE_CANAL_MAP and (agora - CACHE_TIMESTAMP < CACHE_TTL):
        return True

    print("🔄 Atualizando mapa interno de canais M3U do servidor...")
    
    for conta in POOL_CONTAS:
        url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus&output=ts"
        try:
            r = requests.get(url_m3u, headers=HEADERS, timeout=12, verify=False)
            if r.status_code == 200 and "#EXTM3U" in r.text:
                novo_mapa = {}
                linhas = r.text.splitlines()
                canal_atual_nome = None
                
                for linha in linhas:
                    linha_str = linha.strip()
                    if linha_str.startswith("#EXTINF"):
                        # Extrai o nome do canal após a vírgula
                        match_nome = re.search(r',([^,]+)$', linha_str)
                        if match_nome:
                            canal_atual_nome = match_nome.group(1).strip()
                    elif linha_str.startswith("http") and canal_atual_nome:
                        # Extrai o ID do stream ou o caminho relativo (/live/user/pass/ID.ts)
                        match_id = re.search(r'/(?:live/[^/]+/[^/]+/)?([^/]+\.(?:ts|m3u8))$', linha_str)
                        if match_id:
                            stream_filename = match_id.group(1)
                            novo_mapa[canal_atual_nome.lower()] = stream_filename
                            
                            # Palavras-chave curtas para busca rápida
                            nome_limpo = canal_atual_nome.lower()
                            if "premiere 1" in nome_limpo or "premiere fc 1" in nome_limpo:
                                novo_mapa["premiere1"] = stream_filename
                            elif "premiere 2" in nome_limpo:
                                novo_mapa["premiere2"] = stream_filename
                            elif "sportv 1" in nome_limpo or "sportv hd" in nome_limpo:
                                novo_mapa["sportv1"] = stream_filename
                            elif "espn 1" in nome_limpo or "espn hd" in nome_limpo:
                                novo_mapa["espn1"] = stream_filename
                        canal_atual_nome = None
                
                if novo_mapa:
                    CACHE_CANAL_MAP = novo_mapa
                    CACHE_M3U_RAW = r.text
                    CACHE_TIMESTAMP = agora
                    print(f"✅ Mapa de canais carregado com sucesso! ({len(novo_mapa)} identificadores capturados)")
                    return True
        except Exception as e:
            print(f"⚠️ Falha ao baixar M3U da conta {conta['user']}: {e}")
            continue

    return False

@app.route("/")
def home():
    return "Servidor Proxy IPTV (v6 - Mapeador Dinâmico de Canais) Ativo!"

@app.route("/playlist.m3u")
@app.route("/playlist.m3u8")
@app.route("/get.php")
def playlist_m3u():
    carregar_e_mapear_canais()
    base_url = request.host_url.rstrip("/")
    
    # Se temos a playlist Premiere ou o M3U, reescrevemos com links do nosso proxy
    stream_file_premiere = CACHE_CANAL_MAP.get("premiere1", "premiere1.ts")
    
    m3u_content = f"""#EXTM3U url-tvg="http://meusrv.top:80/xmltv.php"
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES - PREMIERE",Premiere 1 FHD [1080p / 60FPS]
{base_url}/live/premiere1.ts
"""
    resp = Response(m3u_content, content_type="application/x-mpegURL")
    return adicionar_cors(resp)

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
@app.route("/live/premiere")
def stream_premiere():
    carregar_e_mapear_canais()
    
    # Obtém o ID numérico real do canal Premiere 1 extraído do M3U original
    stream_filename = CACHE_CANAL_MAP.get("premiere1")
    
    if not stream_filename:
        print("⚠️ ID do canal Premiere 1 não encontrado no mapa de canais.")
        return "Canal não mapeado na fonte original.", 404

    print(f"🎬 Iniciando transmissão do Premiere 1 (Stream Real ID: {stream_filename})...")

    # Percorre o pool de contas tentando a transmissão do ID real
    for idx, conta in enumerate(POOL_CONTAS, 1):
        stream_target = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/{stream_filename}"
        
        try:
            req = requests.get(stream_target, headers=HEADERS, stream=True, timeout=8, verify=False)
            
            # Validação crucial: Verifica se é um stream de vídeo TS real (HTTP 200 e tipo vídeo/octeto)
            content_type = req.headers.get("Content-Type", "")
            if req.status_code == 200 and ("video" in content_type or "octet-stream" in content_type or stream_filename.endswith(".ts")):
                
                # Lê o primeiro bloco para garantir que não é uma página HTML de erro com status 200
                primeiro_chunk = next(req.iter_content(chunk_size=4096), None)
                if primeiro_chunk and not primeiro_chunk.startswith(b"<!DOCTYPE") and not primeiro_chunk.startswith(b"<html"):
                    
                    def retransmitir():
                        yield primeiro_chunk
                        for chunk in req.iter_content(chunk_size=32768):
                            yield chunk
                    
                    resp = Response(retransmitir(), content_type="video/mp2t")
                    return adicionar_cors(resp)
        except Exception as e:
            print(f"⚠️ Falha na Conta {idx} ({conta['host']}): {e}")
            continue

    return "Todas as fontes do pool do Premiere estão temporariamente indisponíveis.", 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
