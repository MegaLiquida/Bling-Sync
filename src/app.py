from flask import Flask, request, redirect, url_for, render_template, send_file
import os
import sys
import pandas as pd
from api_client import search_product, get_item_details, get_access_token, refresh_access_token
from data_processor import read_excel_data, write_excel_data, process_products
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL
from dotenv import load_dotenv, set_key

app = Flask(__name__)

# Carrega variáveis de ambiente do .env (para desenvolvimento local)
load_dotenv()

# Diretório para uploads temporários
UPLOAD_FOLDER = '/tmp/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado'
    file = request.files['file']
    if file.filename == '':
        return 'Nenhum arquivo selecionado'
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Processar o arquivo
        access_token, refresh_token = load_tokens()

        if not access_token or not refresh_token:
            # Em um ambiente de produção, isso deve ser tratado de forma diferente (e.g., erro, redirecionamento para autenticação)
            return 'Erro: Tokens de acesso não configurados. Por favor, configure as variáveis de ambiente.'

        try:
            token_data = refresh_access_token(refresh_token)
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            save_tokens(access_token, refresh_token)
        except Exception as e:
            return f'Erro ao renovar tokens de acesso: {e}. Por favor, verifique as variáveis de ambiente.'

        try:
            df = read_excel_data(filepath)
            df_processed = process_products(df, sys.modules[__name__], access_token)
            
            output_filename = "PLANILHA_EANS_ENCONTRADOS.xlsx"
            output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            write_excel_data(df_processed, output_filepath)
            
            return send_file(output_filepath, as_attachment=True, download_name=output_filename)
        except Exception as e:
            return f'Erro ao processar a planilha: {e}'

def save_tokens(access_token, refresh_token):
    # Em um ambiente de produção, não salvar no .env, usar variáveis de ambiente do Render
    if os.getenv("RENDER") != "true": # Verifica se não está no Render
        set_key(os.path.join(os.getcwd(), '.env'), "ACCESS_TOKEN", access_token)
        set_key(os.path.join(os.getcwd(), '.env'), "REFRESH_TOKEN", refresh_token)

def load_tokens():
    # Em um ambiente de produção, carregar diretamente das variáveis de ambiente do Render
    access_token = os.getenv("ACCESS_TOKEN")
    refresh_token = os.getenv("REFRESH_TOKEN")
    return access_token, refresh_token

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.getenv("PORT", 5000))


