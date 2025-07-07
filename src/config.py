import os

# Credenciais da API do Mercado Livre
CLIENT_ID = os.getenv("6215500289592657")
CLIENT_SECRET = os.getenv("a2v6iXzbW9awbyzPY8oJt3RtfmwBtYPl")
REDIRECT_URI = os.getenv("TG-686bd29002ab58000185809c-2538027629", "http://localhost:5000/callback")

# Endpoints da API do Mercado Livre
AUTH_URL = 'https://auth.mercadolivre.com.br/authorization'
TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
API_BASE_URL = 'https://api.mercadolibre.com'

# Site ID para o Mercado Livre Brasil
SITE_ID = 'MLB'


