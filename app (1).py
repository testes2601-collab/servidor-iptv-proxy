import os
import re
import requests
from flask import Flask, Response, request, redirect

app = Flask(__name__)

# ==========================================
# POOL DE CONTAS SELECIONADAS (FAILOVER)
# ==========================================
# Selecionamos as 5 contas mais estáveis e com maior validade/capacidade
ACCOUNTS_POOL = [
    {
        "id": "meusrv_955823677",
        "host": "http://meusrv.top:80",
        "username": "955823677",
        "password": "798597634",
        "max_con": 3
    },
    {
        "id": "meusrv_74468590",
        "host": "http://meusrv.top:80",
        "username": "74468590",
        "password": "448420959",
        "max_con": 3
    },
    {
        "id": "server_723015",
        "host": "http://79.127.243.145:80",
        "username": "723015",
        "password": "VfGrmD",
        "max_con": 3
    },
    {
        "id": "horizon_cmiz0qsdn001",
        "host": "http://horizonmult.sbs:80",
        "username": "cmiz0qsdn001",
        "password": "35998974504",
        "max_con": 2
    },
    {
        "id": "biturl_5181603291",
        "host": "http://play.biturl.vip:80",
        "username": "5181603291",
        "password": "m23bm8a1nup",
        "max_con": 1
    }
]

HEADERS = {
    "User-Agent": "IPTVSimulator/2.0 (SmartTV; Linux)",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

@app.route('/')
def health_check():
    """Rota de verificação de status para o Render e monitoramento."""
    return {"status": "online", "active_pool_size": len(ACCOUNTS_POOL)}, 200

@app.route('/playlist.m3u')
def get_playlist():
    """
    Gera a playlist M3U unificada para carregar na Smart TV / VLC.
    Busca a lista de canais da conta primária ativa.
    """
    host_base = request.host_url.rstrip('/')
    
    for account in ACCOUNTS_POOL:
        try:
            m3u_url = f"{account['host']}/get.php?username={account['username']}&password={account['password']}&type=m3u_plus&output=ts"
            resp = requests.get(m3u_url, headers=HEADERS, timeout=8)
            if resp.status_code == 200 and "#EXTM3U" in resp.text:
                content = resp.text
                
                # Reescreve os links dos canais para apontarem para o nosso Proxy
                # Exemplo: http://server:80/live/user/pass/1234.ts -> http://nosso-render.com/stream/1234.ts
                def replace_stream_url(match):
                    stream_id = match.group(1)
                    return f"{host_base}/stream/{stream_id}.ts"

                pattern = r'http://[^/]+/live/[^/]+/[^/]+/(\d+\.(?:ts|m3u8))'
                modified_m3u = re.sub(pattern, replace_stream_url, content)
                
                return Response(modified_m3u, mimetype='audio/x-mpegurl')
        except Exception as e:
            print(f"⚠️ Erro ao carregar playlist da conta {account['id']}: {e}")
            continue

    return "❌ Erro: Nenhuma conta do pool respondeu ao carregar a playlist.", 503

@app.route('/stream/<stream_id>')
def proxy_stream(stream_id):
    """
    Faz o proxy do canal com Failover Automático.
    Se a conta A falhar ou der 403/500, tenta imediatamente a conta B.
    """
    for account in ACCOUNTS_POOL:
        target_url = f"{account['host']}/live/{account['username']}/{account['password']}/{stream_id}"
        try:
            # Tenta conectar e fazer o stream
            req = requests.get(target_url, headers=HEADERS, stream=True, timeout=5)
            if req.status_code == 200:
                def generate():
                    for chunk in req.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            yield chunk

                content_type = req.headers.get('Content-Type', 'video/mp2t')
                return Response(generate(), mimetype=content_type)
            else:
                print(f"⚠️ Conta {account['id']} retornou HTTP {req.status_code} para {stream_id}. Tentando próxima...")
        except Exception as e:
            print(f"⚠️ Falha na conexão com conta {account['id']}: {e}. Tentando próxima...")
            continue

    return "❌ Canal indisponível em todas as contas do pool.", 502

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
