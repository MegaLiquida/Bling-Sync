import requests
import json
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, API_BASE_URL, SITE_ID

def get_access_token(code):
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(TOKEN_URL, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token):
    payload = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token
    }
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(TOKEN_URL, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def search_product(query, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    # A API do Mercado Livre para busca de itens por query de texto
    # pode ser encontrada em https://developers.mercadolibre.com.br/pt_br/itens-e-buscas
    # O endpoint é /sites/{SITE_ID}/search?q={query}
    url = f'{API_BASE_URL}/sites/{SITE_ID}/search?q={query}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_item_details(item_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    # Para obter detalhes do item, incluindo atributos como EAN (GTIN)
    # O endpoint é /items/{ITEM_ID}
    # Para garantir que todos os atributos sejam retornados, pode ser necessário incluir um parâmetro
    # como include_attributes=all, conforme a documentação mais recente da API.
    # No entanto, a documentação de product-identifiers sugere que o GTIN está disponível no /items/{ITEM_ID}
    # sem um parâmetro adicional específico para atributos.
    url = f'{API_BASE_URL}/items/{item_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


