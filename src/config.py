import os

# Credenciais da API do Mercado Livre
CLIENT_ID = os.getenv("7401826900082952")
CLIENT_SECRET = os.getenv("AtsQ0fxExmiYTE8eE0bAWi1Q1yOL26Jv")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

# Endpoints da API do Mercado Livre
AUTH_URL = 'https://auth.mercadolivre.com.br/authorization'
TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
API_BASE_URL = 'https://api.mercadolibre.com'

# Site ID para o Mercado Livre Brasil
SITE_ID = 'MLB'


