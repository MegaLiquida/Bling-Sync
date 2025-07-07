import os

# Credenciais da API do Mercado Livre
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

# Endpoints da API do Mercado Livre
AUTH_URL = 'https://auth.mercadolivre.com.br/authorization'
TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
API_BASE_URL = 'https://api.mercadolibre.com'

# Site ID para o Mercado Livre Brasil
SITE_ID = 'MLB'


