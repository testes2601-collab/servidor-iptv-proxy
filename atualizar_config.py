# -*- coding: utf-8 -*-
"""
Robô de Atualização Automática de Canais (GitHub Actions / Cron)
Varre as 5 principais contas + conta reserva, extrai os IDs exatos de cada canal selecionado
e gera o arquivo 'stream_config.json' organizado para consumo do servidor no Render.
"""

import os
import re
import json
import datetime
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração dos canais alvo para filtragem e organização
MAPA_CANAIS_ALVO = [
    {
        "id_slug": "premiere1",
        "nome": "Premiere 1 FHD",
        "categoria": "ESPORTES - PREMIERE",
        "tvg_id": "Premiere1.br",
        "logo": "https://i.imgur.com/8Q9Z3v1.png",
        "keywords": ["PREMIERE 1", "PREMIERE FC 1", "PREMIERE HD"]
    },
    {
        "id_slug": "sportv1",
        "nome": "SportV 1 FHD",
        "categoria": "ESPORTES - SPORTV",
        "tvg_id": "Sportv1.br",
        "logo": "https://i.imgur.com/sportv1.png",
        "keywords": ["SPORTV 1", "SPORTV HD", "SPORTV 1 HD"]
    },
    {
        "id_slug": "espn1",
        "nome": "ESPN 1 FHD",
        "categoria": "ESPORTES - ESPN",
        "tvg_id": "Espn1.br",
        "logo": "https://i.imgur.com/espn1.png",
        "keywords": ["ESPN 1", "ESPN HD", "ESPN BRASIL"]
    },
    {
        "id_slug": "globo_sp",
        "nome": "Globo SP FHD",
        "categoria": "VARIEDADES - ABERTOS",
        "tvg_id": "GloboSP.br",
        "logo": "https://i.imgur.com/globosp.png",
        "keywords": ["GLOBO SP", "GLOBO SP HD", "REDE GLOBO SP"]
    }
]

# Pool das 5 Contas Principais + 1 Reserva (Válidas até 2027/2029)
CONTAS_POOL = [
    {"nome_servidor": "meusrv_1", "host": "http://meusrv.top:80", "user": "955823677", "pass": "798597634", "validade": "2027-04-27"},
    {"nome_servidor": "meusrv_2", "host": "http://meusrv.top:80", "user": "74468590", "pass": "448420959", "validade": "2027-03-13"},
    {"nome_servidor": "ono_79", "host": "http://79.127.243.145:80", "user": "723015", "pass": "VfGrmD", "validade": "2026-12-01"},
    {"nome_servidor": "assistirja_1", "host": "http://assistirja.com:80", "user": "p2WzY2", "pass": "WUr5m3", "validade": "2027-01-11"},
    {"nome_servidor": "assistirja_2", "host": "http://assistirja.com:80", "user": "mqKTBr4T7N", "pass": "1794PMUHjcsp", "validade": "2027-01-11"},
    # Fonte Reserva
    {"nome_servidor": "biturl_reserva", "host": "http://play.biturl.vip:80", "user": "5181603291", "pass": "m23bm8a1nup", "validade": "2029-07-17"}
]

HEADERS = {
    "User-Agent": "IPTVSmarters/3.0.0 (Linux; Android 10) VLC/3.0.12"
}

def extrair_mapa_ids(conta):
    """
    Baixa a playlist da conta e faz o mapeamento dos IDs numéricos para cada canal alvo.
    """
    mapa_encontrado = {}
    try:
        url_m3u = f"{conta['host']}/get.php?username={conta['user']}&password={conta['pass']}&type=m3u_plus"
        res = requests.get(url_m3u, headers=HEADERS, timeout=6, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for i, linha in enumerate(linhas):
                if linha.startswith("#EXTINF"):
                    linha_upper = linha.upper()
                    for canal in MAPA_CANAIS_ALVO:
                        slug = canal["id_slug"]
                        if slug in mapa_encontrado:
                            continue
                        if any(kw in linha_upper for kw in canal["keywords"]):
                            if i + 1 < len(linhas) and not linhas[i+1].startswith("#"):
                                match = re.search(r'/(\\d+)\\.(ts|m3u8)', linhas[i+1])
                                if match:
                                    mapa_encontrado[slug] = match.group(1)
    except Exception as e:
        print(f"⚠️ Falha ao ler a conta {conta['nome_servidor']}: {e}")
    return mapa_encontrado

def construir_config_organizada():
    print("🚀 Iniciando varredura das fontes e mapeamento de IDs...")
    
    resultado_canais = {}
    for canal in MAPA_CANAIS_ALVO:
        slug = canal["id_slug"]
        resultado_canais[slug] = {
            "id_slug": slug,
            "nome": canal["nome"],
            "categoria": canal["categoria"],
            "tvg_id": canal["tvg_id"],
            "logo": canal["logo"],
            "fontes": []
        }

    for conta in CONTAS_POOL:
        mapa_ids = extrair_mapa_ids(conta)
        for slug, stream_id in mapa_ids.items():
            prioridade = len(resultado_canais[slug]["fontes"]) + 1
            resultado_canais[slug]["fontes"].append({
                "prioridade": prioridade,
                "nome_servidor": conta["nome_servidor"],
                "host": conta["host"],
                "user": conta["user"],
                "pass": conta["pass"],
                "stream_id": stream_id,
                "validade": conta["validade"]
            })

    dados_finais = {
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_canais": len(resultado_canais),
        "canais": resultado_canais
    }

    with open("stream_config.json", "w", encoding="utf-8") as f:
        json.dump(dados_finais, f, indent=2, ensure_ascii=False)

    print(f"✅ Arquivo 'stream_config.json' gerado com sucesso contendo {len(resultado_canais)} canais catalogados!")

if __name__ == "__main__":
    construir_config_organizada()
