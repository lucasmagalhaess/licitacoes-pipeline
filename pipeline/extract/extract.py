import requests
import json
import os
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient

STORAGE_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
API_KEY = os.environ.get("PORTAL_API_KEY", "9b90291f3f65d5615591d56a71d0f15f")
CONTAINER_BRONZE = "bronze"

# Principais órgãos do governo federal
ORGAOS = {
    "25000": "Ministério da Fazenda",
    "36000": "Ministério da Saúde",
    "26000": "Ministério da Educação",
    "39000": "Ministério da Infraestrutura",
    "30000": "Ministério da Defesa",
    "52000": "Ministério da Justiça",
}

def get_contratos(codigo_orgao, pagina=1):
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos"
    headers = {"chave-api-dados": API_KEY}
    params = {"codigoOrgao": codigo_orgao, "pagina": pagina}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def save_to_blob(data, blob_name):
    client = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
    container = client.get_container_client(CONTAINER_BRONZE)
    container.upload_blob(
        name=blob_name,
        data=json.dumps(data, ensure_ascii=False, indent=2),
        overwrite=True,
        content_settings=None
    )
    print(f"Salvo no Blob Storage: {blob_name}")

def extract():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")

    todos_contratos = []

    for codigo, nome in ORGAOS.items():
        print(f"Extraindo contratos: {nome}...")
        try:
            contratos = get_contratos(codigo)
            for c in contratos:
                c["orgao_nome"] = nome
                c["orgao_codigo"] = codigo
            todos_contratos.extend(contratos)
            print(f"  {len(contratos)} contratos extraídos")
        except Exception as e:
            print(f"  Erro em {nome}: {e}")

    payload = {
        "extraction_date": today,
        "extraction_timestamp": timestamp,
        "total_contratos": len(todos_contratos),
        "contratos": todos_contratos
    }

    blob_name = f"licitacoes/{today}/contratos_{timestamp.replace(':', '-')}.json"
    save_to_blob(payload, blob_name)

    print(f"\nTotal extraído: {len(todos_contratos)} contratos")
    return blob_name

if __name__ == "__main__":
    extract()
