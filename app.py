# -*- coding: utf-8 -*-
"""
===============================================================================
SERVIDOR PROXY IPTV PREMIUM - GERENCIADOR AUTOMÁTICO PREMIERE 1
===============================================================================
Este servidor Flask foi desenvolvido para processar, filtrar e retransmitir
o sinal do canal Premiere 1 FHD a partir de múltiplas fontes M3U/Xtream Codes.

Recursos principais:
1. Rota de diagnóstico /debug (e /debug/) em Português completo.
2. Web Player integrado na rota /watch para assistir direto pelo Chrome.
3. Lista M3U gerada na rota /playlist.m3u para Smart TVs e aplicativos IPTV.
4. Rota de transmissão de mídia em /live/premiere1.ts.
5. Inspeção profunda de pacotes anti-Cloudflare e anti-HTML de erro.
6. Rodízio e substituição automática entre dezenas de contas do pool.
7. Tratamento global de erros 404 e 500 para evitar mensagens genéricas.
===============================================================================
"""

import os
import re
import time
import logging
import urllib3
import requests
from flask import Flask, Response, request, redirect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

LISTA_CONTAS_POOL = [
    {
        "id": "ip_103_01",
        "nome": "Servidor IP 103 (Conta 1)",
        "host": "http://103.176.90.186:80",
        "user": "e0828d9135",
        "pass": "e91802270546",
        "tipo": "ip_direto"
    },
    {
        "id": "ip_103_02",
        "nome": "Servidor IP 103 (Conta 2)",
        "host": "http://103.176.90.186:80",
        "user": "7b559c1042",
        "pass": "11de4cebb4",
        "tipo": "ip_direto"
    },
    {
        "id": "ono_79_01",
        "nome": "Servidor ONO IP 79",
        "host": "http://79.127.243.145:80",
        "user": "723015",
        "pass": "VfGrmD",
        "tipo": "ip_direto"
    },
    {
        "id": "ono_85_01",
        "nome": "Servidor ONO IP 85 (Otavio)",
        "host": "http://85.137.49.157.dyn.user.ono.com:80",
        "user": "Otaviodeledove",
        "pass": "9Dh5R8uAu5",
        "tipo": "ip_direto"
    },
    {
        "id": "ono_85_02",
        "nome": "Servidor ONO IP 85 (Tatiana)",
        "host": "http://85.137.49.157.dyn.user.ono.com:80",
        "user": "tatiana9944",
        "pass": "Ta994a",
        "tipo": "ip_direto"
    },
    {
        "id": "meusrv_01",
        "nome": "MeuSrv 955",
        "host": "http://meusrv.top:80",
        "user": "955823677",
        "pass": "798597634",
        "tipo": "dominio"
    },
    {
        "id": "meusrv_02",
        "nome": "MeuSrv 744",
        "host": "http://meusrv.top:80",
        "user": "74468590",
        "pass": "448420959",
        "tipo": "dominio"
    },
    {
        "id": "meusrv_03",
        "nome": "MeuSrv 567",
        "host": "http://meusrv.top:80",
        "user": "567689135",
        "pass": "965722522",
        "tipo": "dominio"
    },
    {
        "id": "meusrv_04",
        "nome": "MeuSrv 361",
        "host": "http://meusrv.top:80",
        "user": "361811331",
        "pass": "252766314",
        "tipo": "dominio"
    },
    {
        "id": "xyz_332_01",
        "nome": "XYZ 332 (988)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "988060",
        "pass": "zd7YEw",
        "tipo": "dominio"
    },
    {
        "id": "xyz_332_02",
        "nome": "XYZ 332 (Constancio)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "constancio79",
        "pass": "Wagner@79",
        "tipo": "dominio"
    },
    {
        "id": "xyz_332_03",
        "nome": "XYZ 332 (Casa na Praia)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "Casanapraia10",
        "pass": "Tvfuturo2",
        "tipo": "dominio"
    },
    {
        "id": "z2mu_54_01",
        "nome": "54z2mu Pro",
        "host": "http://54z2mu.pro:80",
        "user": "jT63beuY",
        "pass": "F11Gkd",
        "tipo": "dominio"
    },
    {
        "id": "fftq_49_01",
        "nome": "49fftq Live (Wellgton)",
        "host": "http://49fftq.live:80",
        "user": "WellgtonSilva35",
        "pass": "991DNEubv",
        "tipo": "dominio"
    },
    {
        "id": "vector_61_01",
        "nome": "Vector CDN 61",
        "host": "http://61701-vector.cdn-o2.me:80",
        "user": "4df74cf07e",
        "pass": "9d49be6b44bc",
        "tipo": "dominio"
    },
    {
        "id": "given_11_01",
        "nome": "Given CDN 11",
        "host": "http://11359-given.cdn-o2.me:80",
        "user": "4af01daf4f",
        "pass": "7e3498490571",
        "tipo": "dominio"
    },
    {
        "id": "biturl_play_01",
        "nome": "Biturl Play (518)",
        "host": "http://play.biturl.vip:80",
        "user": "5181603291",
        "pass": "m23bm8a1nup",
        "tipo": "dominio"
    }
]

HEADERS_CLIENTE = {
    "User-Agent": "TiviMate/4.6.1 (Android TV; BRAVIA 4K UR3)",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def adicionar_cabecalhos_cors(resposta):
    resposta.headers["Access-Control-Allow-Origin"] = "*"
    resposta.headers["Access-Control-Allow-Headers"] = "*"
    resposta.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, HEAD"
    return resposta

def extrair_stream_id_real(conta_info):
    host = conta_info["host"]
    user = conta_info["user"]
    password = conta_info["pass"]
    
    url_m3u = f"{host}/get.php?username={user}&password={password}&type=m3u_plus"
    try:
        res = requests.get(url_m3u, headers=HEADERS_CLIENTE, timeout=4, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for index, linha in enumerate(linhas):
                linha_upper = linha.upper()
                if "PREMIERE 1" in linha_upper or "PREMIERE FC 1" in linha_upper or "PREMIERE HD" in linha_upper:
                    if index + 1 < len(linhas):
                        prox_linha = linhas[index + 1].strip()
                        if prox_linha and not prox_linha.startswith("#"):
                            match = re.search(r'/(\d+)\.(ts|m3u8)', prox_linha)
                            if match:
                                return match.group(1)
    except Exception as e:
        logging.warning(f"Erro ao extrair ID numérico na conta {conta_info['id']}: {e}")
    
    return "premiere1"

def validar_se_e_video_valido(chunk_bytes):
    if not chunk_bytes:
        return False
    
    amostra = chunk_bytes[:1024].lower()
    palavras_invalidas = [
        b"<html", b"<!doctype", b"cloudflare", b"restricted",
        b"stream not found", b"access denied", b"404 not found",
        b"service unavailable", b"error 1020"
    ]
    
    for termo in palavras_invalidas:
        if termo in amostra:
            return False
            
    return True

def tentar_conectar_stream(conta_info):
    stream_id = extrair_stream_id_real(conta_info)
    target_url = f"{conta_info['host']}/live/{conta_info['user']}/{conta_info['pass']}/{stream_id}.ts"
    
    try:
        res = requests.get(target_url, headers=HEADERS_CLIENTE, stream=True, timeout=5, verify=False)
        if res.status_code == 200:
            iterador = res.iter_content(chunk_size=32768)
            primeiro_chunk = next(iterador, None)
            
            if primeiro_chunk and validar_se_e_video_valido(primeiro_chunk):
                def gerador_de_fluxo():
                    yield primeiro_chunk
                    for chunk in iterador:
                        if chunk:
                            yield chunk
                return gerador_de_fluxo()
    except Exception as err:
        logging.error(f"Falha na conexão com a conta {conta_info['id']}: {err}")
        
    return None

@app.errorhandler(404)
def erro_pagina_nao_encontrada(e):
    html_404 = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Página Não Encontrada - Servidor Proxy IPTV</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 40px; text-align: center; }
            .box { background-color: #1e1e1e; border-radius: 12px; padding: 30px; display: inline-block; max-width: 600px; }
            h2 { color: #ff5252; }
            p { color: #cccccc; }
            .btn { display: inline-block; background-color: #00e676; color: #000; font-weight: bold; padding: 12px 20px; border-radius: 6px; text-decoration: none; margin: 8px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>⚠️ Endereço Não Encontrado</h2>
            <p>O endereço solicitado não existe neste servidor proxy. Por favor, utilize uma das opções oficiais abaixo:</p>
            <br>
            <a href="/" class="btn">🏠 Página Inicial</a>
            <a href="/debug" class="btn">📊 Diagnosticador (/debug)</a>
            <a href="/watch" class="btn">📺 Web Player (/watch)</a>
            <a href="/playlist.m3u" class="btn">📋 Lista M3U (/playlist.m3u)</a>
        </div>
    </body>
    </html>
    """
    return adicionar_cabecalhos_cors(Response(html_404, status=404, content_type="text/html; charset=utf-8"))

@app.errorhandler(500)
def erro_interno_servidor(e):
    html_500 = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Erro Interno - Servidor Proxy IPTV</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 40px; text-align: center; }
            .box { background-color: #1e1e1e; border-radius: 12px; padding: 30px; display: inline-block; max-width: 600px; }
            h2 { color: #ffb74d; }
            .btn { display: inline-block; background-color: #29b6f6; color: #000; font-weight: bold; padding: 12px 20px; border-radius: 6px; text-decoration: none; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>⚙️ Ocorreu uma oscilação temporária no servidor</h2>
            <p>O sistema tentou reprocessar a requisição e encontrou uma interrupção temporária. Tente recarregar a página.</p>
            <a href="/debug" class="btn">Abrir Diagnóstico (/debug)</a>
        </div>
    </body>
    </html>
    """
    return adicionar_cabecalhos_cors(Response(html_500, status=500, content_type="text/html; charset=utf-8"))

@app.route("/")
def rota_home():
    html_home = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Servidor Proxy IPTV - Premiere 1 FHD</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 30px; text-align: center; }
            .card { background-color: #1e1e1e; border-radius: 12px; padding: 30px; display: inline-block; max-width: 650px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
            h1 { color: #00e676; margin-bottom: 5px; }
            p { color: #b0bec5; }
            .btn-group { margin-top: 25px; }
            .btn { background-color: #00e676; color: #000; font-weight: bold; padding: 14px 22px; border-radius: 8px; margin: 8px; display: inline-block; text-decoration: none; }
            .btn-alt { background-color: #29b6f6; color: #000; font-weight: bold; padding: 14px 22px; border-radius: 8px; margin: 8px; display: inline-block; text-decoration: none; }
            .btn-dark { background-color: #424242; color: #fff; font-weight: bold; padding: 14px 22px; border-radius: 8px; margin: 8px; display: inline-block; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>⚽ Servidor Proxy IPTV Premiere 1</h1>
            <p>Gerenciador e redirecionador inteligente de alta disponibilidade para Smart TV e Web.</p>
            <div class="btn-group">
                <a href="/debug" class="btn">📊 Diagnosticador (/debug)</a>
                <a href="/watch" class="btn-alt">📺 Web Player (/watch)</a>
                <a href="/playlist.m3u" class="btn-dark">📋 Playlist M3U (/playlist.m3u)</a>
            </div>
        </div>
    </body>
    </html>
    """
    return adicionar_cabecalhos_cors(Response(html_home, content_type="text/html; charset=utf-8"))

@app.route("/debug")
@app.route("/debug/")
def rota_debug():
    inicio_tempo = time.time()
    relatorio_linhas = []
    
    total_contas = len(LISTA_CONTAS_POOL)
    contas_online = 0
    contas_offline = 0
    
    for conta in LISTA_CONTAS_POOL:
        status_texto = ""
        cor_status = "red"
        detalhes = ""
        
        url_teste = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        try:
            r = requests.head(url_teste, headers=HEADERS_CLIENTE, timeout=3, verify=False)
            if r.status_code == 200:
                status_texto = "ONLINE (HTTP 200 - Sinal Limpo)"
                cor_status = "#00e676"
                contas_online += 1
            elif r.status_code in [301, 302, 307, 308]:
                status_texto = f"REDIRECIONADO (HTTP {r.status_code})"
                cor_status = "#ffb74d"
                contas_online += 1
            else:
                status_texto = f"RESPOSTA ANÔMALA (HTTP {r.status_code})"
                cor_status = "#ff5252"
                contas_offline += 1
        except Exception as err_exp:
            status_texto = "OFFLINE OU BLOQUEADO"
            cor_status = "#ff5252"
            detalhes = f" ({type(err_exp).__name__})"
            contas_offline += 1

        linha_html = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #333;"><b>{conta['nome']}</b></td>
            <td style="padding: 10px; border-bottom: 1px solid #333;"><code>{conta['host']}</code></td>
            <td style="padding: 10px; border-bottom: 1px solid #333; color: {cor_status}; font-weight: bold;">{status_texto}{detalhes}</td>
        </tr>
        """
        relatorio_linhas.append(linha_html)

    tempo_decorrido = round(time.time() - inicio_tempo, 2)
    
    template_debug = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Diagnóstico do Servidor Proxy IPTV</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background-color: #1e1e1e; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }}
            h2 {{ color: #00e676; border-bottom: 2px solid #00e676; padding-bottom: 10px; }}
            .summary {{ display: flex; justify-content: space-between; background: #2a2a2a; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background-color: #2c2c2c; color: #00e676; text-align: left; padding: 12px; }}
            .btn-voltar {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #29b6f6; color: #000; font-weight: bold; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📊 Relatório de Saúde do Pool de Servidores M3U</h2>
            <div class="summary">
                <div><b>Total Mapeado:</b> {total_contas}</div>
                <div><b style="color: #00e676;">Contas Online:</b> {contas_online}</div>
                <div><b style="color: #ff5252;">Contas Inativas:</b> {contas_offline}</div>
                <div><b>Tempo:</b> {tempo_decorrido}s</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Nome do Servidor</th>
                        <th>Endereço do Host</th>
                        <th>Status do Sinal</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(relatorio_linhas)}
                </tbody>
            </table>
            <br>
            <a href="/" class="btn-voltar">← Voltar para o Início</a>
        </div>
    </body>
    </html>
    """
    return adicionar_cabecalhos_cors(Response(template_debug, content_type="text/html; charset=utf-8"))

@app.route("/watch")
@app.route("/watch/")
def rota_watch():
    html_player = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Web Player - Premiere 1 FHD</title>
        <link href="https://vjs.zencdn.net/7.20.3/video-js.css" rel="stylesheet" />
        <style>
            body { font-family: Arial, sans-serif; background-color: #0a0a0a; color: #fff; text-align: center; margin: 0; padding: 20px; }
            .player-box { max-width: 900px; margin: 20px auto; background-color: #161616; padding: 20px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); }
            h1 { color: #00e676; margin-bottom: 10px; }
            .video-js { margin: 0 auto; border-radius: 8px; overflow: hidden; width: 100%; height: 500px; }
            .badge { background-color: #ff1744; color: #fff; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="player-box">
            <h1>⚽ Premiere 1 FHD <span class="badge">AO VIVO</span></h1>
            <p>Transmissão em tempo real decodificada diretamente pelo navegador Chrome</p>
            <video id="player-premiere" class="video-js vjs-default-skin vjs-big-play-centered" controls autoplay preload="auto">
                <source src="/live/premiere1.ts" type="video/mp2t">
            </video>
        </div>
        <script src="https://vjs.zencdn.net/7.20.3/video.min.js"></script>
    </body>
    </html>
    """
    return adicionar_cabecalhos_cors(Response(html_player, content_type="text/html; charset=utf-8"))

@app.route("/playlist.m3u")
def rota_playlist():
    host_base = request.host_url.rstrip("/")
    conteudo_m3u = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{host_base}/live/premiere1.ts
"""
    resp = Response(conteudo_m3u, content_type="application/x-mpegURL")
    return adicionar_cabecalhos_cors(resp)

@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def rota_stream_premiere():
    for conta in LISTA_CONTAS_POOL:
        fluxo_video = tentar_conectar_stream(conta)
        if fluxo_video:
            logging.info(f"Transmissão iniciada com sucesso usando a conta: {conta['id']}")
            resposta = Response(fluxo_video, content_type="video/mp2t")
            return adicionar_cabecalhos_cors(resposta)

    logging.error("Todas as contas do pool falharam ao entregar o vídeo.")
    mensagem_erro = "Todas as contas do pool estão indisponíveis no momento. Tente novamente em instantes."
    return adicionar_cabecalhos_cors(Response(mensagem_erro, status=503, content_type="text/plain; charset=utf-8"))

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    logging.info(f"Iniciando Servidor Proxy IPTV na porta {porta}...")
    app.run(host="0.0.0.0", port=porta, debug=False)
