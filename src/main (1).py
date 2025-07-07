import os
import sys
import pandas as pd
from api_client import search_product, get_item_details, get_access_token, refresh_access_token
from data_processor import read_excel_data, write_excel_data, process_products
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, ENV_PATH
from dotenv import load_dotenv, set_key

def save_tokens(access_token, refresh_token):
    set_key(ENV_PATH, "ACCESS_TOKEN", access_token)
    set_key(ENV_PATH, "REFRESH_TOKEN", refresh_token)

def load_tokens():
    load_dotenv(ENV_PATH)
    return os.getenv("ACCESS_TOKEN"), os.getenv("REFRESH_TOKEN")

def main():
    print("Iniciando o sistema de busca de EANs...")

    # 1. Carregar tokens existentes ou iniciar fluxo de autenticação
    access_token, refresh_token = load_tokens()

    if not access_token or not refresh_token:
        print("Nenhum token de acesso encontrado. Iniciando fluxo de autenticação...")
        auth_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        print(f"Por favor, acesse esta URL no seu navegador para autorizar a aplicação:\n{auth_url}")
        auth_code = input("Após autorizar, cole o código de autorização aqui: ")
        try:
            token_data = get_access_token(auth_code)
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            save_tokens(access_token, refresh_token)
            print("Tokens de acesso obtidos e salvos com sucesso!")
        except Exception as e:
            print(f"Erro ao obter tokens de acesso: {e}")
            sys.exit(1)
    else:
        print("Tokens de acesso encontrados. Tentando renovar...")
        try:
            token_data = refresh_access_token(refresh_token)
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            save_tokens(access_token, refresh_token)
            print("Tokens de acesso renovados com sucesso!")
        except Exception as e:
            print(f"Erro ao renovar tokens de acesso: {e}. Por favor, reinicie o processo de autenticação.\n{e}")
            # Limpar tokens inválidos para forçar nova autenticação
            set_key(ENV_PATH, "ACCESS_TOKEN", "")
            set_key(ENV_PATH, "REFRESH_TOKEN", "")
            sys.exit(1)

    # 2. Definir caminhos de arquivo
    input_file = "/home/ubuntu/upload/PLANILHA(1)(1).xlsx" # Caminho da planilha de entrada
    output_file = "/home/ubuntu/ean_search_system/PLANILHA_EANS_ENCONTRADOS.xlsx" # Caminho da planilha de saída

    if not os.path.exists(input_file):
        print(f"Erro: O arquivo de entrada não foi encontrado em {input_file}")
        sys.exit(1)

    # 3. Ler a planilha
    print(f"Lendo a planilha: {input_file}")
    try:
        df = read_excel_data(input_file)
        print("Planilha lida com sucesso. Primeiras 5 linhas:")
        print(df.head().to_markdown(index=False))
    except Exception as e:
        print(f"Erro ao ler a planilha: {e}")
        sys.exit(1)

    # 4. Processar produtos e buscar EANs
    print("Iniciando busca de EANs para os produtos...")
    df_processed = process_products(df, sys.modules[__name__], access_token) # Passa o módulo atual para acesso às funções da API

    # 5. Salvar a planilha com os EANs
    print(f"Salvando resultados em: {output_file}")
    try:
        write_excel_data(df_processed, output_file)
        print("Processo concluído. Planilha com EANs salva com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar a planilha: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


