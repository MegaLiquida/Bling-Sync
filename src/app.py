from flask import Flask, request, redirect, url_for, render_template, send_from_directory, jsonify, session
from flask_session import Session
import os
import pandas as pd
from api_client import search_product, get_item_details, get_access_token, refresh_access_token
from data_processor import read_excel_data, write_excel_data, process_products
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, API_BASE_URL, SECRET_KEY, UPLOAD_FOLDER, DATABASE_URL
from dotenv import load_dotenv, set_key
import sqlite3
from datetime import datetime, timedelta
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from io import BytesIO

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env (para desenvolvimento local)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', SECRET_KEY)

# Configuração para sessões do Flask
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
Session(app)

# Diretório para uploads temporários
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configuração do banco de dados
def get_db_connection():
    db_url = os.getenv('DATABASE_URL', DATABASE_URL)
    if db_url.startswith('sqlite://'):
        db_path = db_url.replace('sqlite://', '')
        conn = sqlite3.connect(db_path)
    else:
        # Para PostgreSQL ou outros bancos de dados, você precisaria de um driver como psycopg2
        # Exemplo para PostgreSQL (requer psycopg2 instalado):
        import psycopg2
        conn = psycopg2.connect(db_url)
    conn.row_factory = sqlite3.Row # Permite acessar colunas como dicionário
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos_enviados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ean TEXT NOT NULL,
            nome TEXT,
            cor TEXT,
            voltagem TEXT,
            modelo TEXT,
            quantidade INTEGER,
            data_envio TEXT,
            usuario_id INTEGER,
            usuario_nome TEXT,
            validado BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (usuario_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listas_unificadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_lista TEXT NOT NULL,
            responsavel_validacao TEXT NOT NULL,
            data_criacao TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos_unificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lista_unificada_id INTEGER NOT NULL,
            ean TEXT NOT NULL,
            nome TEXT,
            cor TEXT,
            voltagem TEXT,
            modelo TEXT,
            quantidade INTEGER NOT NULL,
            origem_listas TEXT, -- JSON string of original list IDs and quantities
            FOREIGN KEY (lista_unificada_id) REFERENCES listas_unificadas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_atividade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo_atividade TEXT NOT NULL, -- 'consulta' ou 'envio'
            ean TEXT,
            nome_produto TEXT,
            quantidade INTEGER,
            data_atividade TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES users(id)
        )
    ''')
    conn.commit()

    # Adicionar usuário admin padrão se não existir
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('admin')
        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', ('admin', hashed_password, True))
        conn.commit()
        logging.info('Usuário admin padrão criado.')

    conn.close()

# Inicializa o banco de dados ao iniciar a aplicação
with app.app_context():
    init_database()

# Decorador para verificar autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            logging.info(f'Usuário {username} logado com sucesso.')
            return redirect(url_for('index'))
        else:
            logging.warning(f'Tentativa de login falhou para o usuário {username}.')
            return render_template('login.html', error='Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    logging.info('Usuário deslogado.')
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Itens por página
    offset = (page - 1) * per_page

    # Parâmetros de filtro
    search_query = request.args.get('search', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    query = 'SELECT * FROM produtos_enviados WHERE 1=1'
    params = []

    if search_query:
        query += ' AND (ean LIKE ? OR nome LIKE ? OR cor LIKE ? OR voltagem LIKE ? OR modelo LIKE ?)'
        params.extend([f'%{search_query}%'] * 5)
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
            query += ' AND data_envio >= ?'
            params.append(start_date)
        except ValueError:
            logging.warning(f'Formato de data inválido para data_inicio: {start_date_str}')

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
            query += ' AND data_envio <= ?'
            params.append(end_date)
        except ValueError:
            logging.warning(f'Formato de data inválido para data_fim: {end_date_str}')

    # Contar o total de itens para paginação
    total_items = conn.execute(query.replace('*', 'COUNT(*)'), params).fetchone()[0]
    total_pages = (total_items + per_page - 1) // per_page

    # Adicionar ordenação e limites para paginação
    query += ' ORDER BY data_envio DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    produtos = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin.html', produtos=produtos, page=page, total_pages=total_pages, search_query=search_query, start_date=start_date_str, end_date=end_date_str)

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['username'])

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        try:
            df = read_excel_data(filepath)
            processed_data = process_products(df)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            for item in processed_data:
                cursor.execute(
                    'INSERT INTO produtos_enviados (ean, nome, cor, voltagem, modelo, quantidade, data_envio, usuario_id, usuario_nome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (item['EAN'], item['Nome'], item['Cor'], item['Voltagem'], item['Modelo'], item['Quantidade'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['user_id'], session['username']))
                
                # Registrar log de atividade para cada produto enviado
                registrar_log_atividade(session['user_id'], 'envio', item['EAN'], item['Nome'], item['Quantidade'])

            conn.commit()
            conn.close()
            os.remove(filepath) # Remover arquivo temporário
            logging.info(f'Arquivo {file.filename} processado e dados salvos por {session['username']}.')
            return jsonify({'message': 'Arquivo processado com sucesso!'}), 200
        except Exception as e:
            logging.error(f'Erro ao processar arquivo {file.filename}: {e}')
            return jsonify({'error': f'Erro ao processar arquivo: {e}'}), 500
    else:
        return jsonify({'error': 'Formato de arquivo não suportado. Use .xlsx ou .xls'}), 400

@app.route('/api/validar-lista/<int:produto_id>', methods=['POST'])
@login_required
def validar_lista(produto_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE produtos_enviados SET validado = 1 WHERE id = ?', (produto_id,))
    conn.commit()
    conn.close()
    logging.info(f'Lista {produto_id} validada pelo admin {session['username']}.')
    return jsonify({'message': 'Lista validada com sucesso!'}), 200

@app.route('/api/validar-listas-lote', methods=['POST'])
@login_required
def validar_listas_lote():
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    lista_ids = request.json.get('lista_ids', [])
    if not lista_ids:
        return jsonify({'error': 'Nenhum ID de lista fornecido'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    listas_validadas_com_sucesso = []
    listas_com_erro = []

    for lista_id in lista_ids:
        try:
            # Marcar a lista como validada
            cursor.execute('UPDATE produtos_enviados SET validado = 1 WHERE id = ?', (lista_id,))
            
            # Obter os produtos da lista validada para unificação
            produtos_da_lista = conn.execute('SELECT ean, nome, cor, voltagem, modelo, quantidade, usuario_nome, data_envio FROM produtos_enviados WHERE id = ?', (lista_id,)).fetchone()
            
            if produtos_da_lista:
                listas_validadas_com_sucesso.append(lista_id)
            else:
                listas_com_erro.append({'id': lista_id, 'erro': 'Lista não encontrada ou sem produtos.'})

        except Exception as e:
            conn.rollback() # Reverter em caso de erro
            logging.error(f'Erro ao validar lista {lista_id}: {e}')
            listas_com_erro.append({'id': lista_id, 'erro': str(e)})
    
    # Criar lista unificada após processar todas as validações
    if listas_validadas_com_sucesso:
        try:
            criar_lista_unificada(listas_validadas_com_sucesso, session['username'], conn)
            conn.commit()
            logging.info(f'Listas {listas_validadas_com_sucesso} validadas e unificadas pelo admin {session['username']}.')
        except Exception as e:
            conn.rollback()
            logging.error(f'Erro ao criar lista unificada para IDs {listas_validadas_com_sucesso}: {e}')
            return jsonify({'error': f'Erro ao criar lista unificada: {e}'}), 500
    else:
        conn.commit() # Commit any individual validations even if no unificada list was created

    conn.close()

    if listas_com_erro:
        return jsonify({'message': 'Algumas listas foram validadas, mas ocorreram erros em outras.', 'erros': listas_com_erro}), 200
    else:
        return jsonify({'message': 'Listas validadas e unificadas com sucesso!'}), 200

def criar_lista_unificada(lista_ids, responsavel_validacao, conn):
    logging.info(f'Iniciando criação de lista unificada para IDs: {lista_ids} por {responsavel_validacao}')
    cursor = conn.cursor()
    
    # Criar nova lista unificada
    nome_lista = f'Lista_Unificada_{responsavel_validacao}_{datetime.now().strftime('%Y%m%d%H%M%S')}'
    data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO listas_unificadas (nome_lista, responsavel_validacao, data_criacao) VALUES (?, ?, ?)', (nome_lista, responsavel_validacao, data_criacao))
    lista_unificada_id = cursor.lastrowid
    logging.info(f'Nova lista unificada criada com ID: {lista_unificada_id} e nome: {nome_lista}')

    produtos_unificados_dict = {}
    
    for lista_id in lista_ids:
        logging.info(f'Processando produtos da lista ID: {lista_id}')
        # Buscar todos os produtos da lista original (não apenas o primeiro)
        produtos_originais = conn.execute('SELECT ean, nome, cor, voltagem, modelo, quantidade, usuario_nome, data_envio FROM produtos_enviados WHERE id = ?', (lista_id,)).fetchall()
        
        if not produtos_originais:
            logging.warning(f'Lista ID {lista_id} não encontrada ou sem produtos. Ignorando.')
            continue

        for produto in produtos_originais:
            ean = produto['ean']
            nome = produto['nome']
            cor = produto['cor']
            voltagem = produto['voltagem']
            modelo = produto['modelo']
            quantidade = produto['quantidade']
            usuario_origem = produto['usuario_nome']
            data_origem = produto['data_envio']

            if not ean:
                logging.warning(f'Produto com EAN vazio na lista {lista_id}. Ignorando: {produto}.')
                continue
            if quantidade is None or quantidade <= 0:
                logging.warning(f'Produto com quantidade inválida na lista {lista_id}. Ignorando: {produto}.')
                continue

            if ean not in produtos_unificados_dict:
                produtos_unificados_dict[ean] = {
                    'nome': nome,
                    'cor': cor,
                    'voltagem': voltagem,
                    'modelo': modelo,
                    'quantidade': quantidade,
                    'origem_listas': [{'id': lista_id, 'usuario': usuario_origem, 'data': data_origem, 'quantidade': quantidade}]
                }
                logging.info(f'Adicionado novo produto EAN {ean} com quantidade {quantidade}.')
            else:
                produtos_unificados_dict[ean]['quantidade'] += quantidade
                produtos_unificados_dict[ean]['origem_listas'].append({'id': lista_id, 'usuario': usuario_origem, 'data': data_origem, 'quantidade': quantidade})
                logging.info(f'Produto EAN {ean} já existe. Quantidade atualizada para {produtos_unificados_dict[ean]['quantidade']}.')

    # Inserir produtos unificados no banco de dados
    for ean, data in produtos_unificados_dict.items():
        cursor.execute(
            'INSERT INTO produtos_unificados (lista_unificada_id, ean, nome, cor, voltagem, modelo, quantidade, origem_listas) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (lista_unificada_id, ean, data['nome'], data['cor'], data['voltagem'], data['modelo'], data['quantidade'], str(data['origem_listas'])))
        logging.info(f'Produto unificado EAN {ean} inserido na lista {lista_unificada_id}.')
    
    logging.info(f'Criação de lista unificada {lista_unificada_id} concluída.')

@app.route('/listas-unificadas')
@login_required
def listas_unificadas():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    listas = carregar_listas_unificadas(conn)
    conn.close()
    return render_template('listas_unificadas.html', listas=listas)

def carregar_listas_unificadas(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM listas_unificadas ORDER BY data_criacao DESC')
    listas = cursor.fetchall()
    
    # Adicionar contagem de produtos para cada lista
    listas_com_contagem = []
    for lista in listas:
        produtos_count = conn.execute('SELECT COUNT(*) FROM produtos_unificados WHERE lista_unificada_id = ?', (lista['id'],)).fetchone()[0]
        total_quantidade = conn.execute('SELECT SUM(quantidade) FROM produtos_unificados WHERE lista_unificada_id = ?', (lista['id'],)).fetchone()[0]
        lista_dict = dict(lista) # Converter Row para dict para adicionar novas chaves
        lista_dict['produtos_count'] = produtos_count
        lista_dict['total_quantidade'] = total_quantidade if total_quantidade else 0
        listas_com_contagem.append(lista_dict)
    
    return listas_com_contagem

@app.route('/listas-unificadas/<int:lista_id>')
@login_required
def detalhes_lista_unificada(lista_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    lista = conn.execute('SELECT * FROM listas_unificadas WHERE id = ?', (lista_id,)).fetchone()
    produtos = carregar_produtos_lista_unificada(lista_id, conn)
    conn.close()

    if lista:
        return render_template('detalhes_lista_unificada.html', lista=lista, produtos=produtos)
    else:
        return 'Lista não encontrada', 404

def carregar_produtos_lista_unificada(lista_unificada_id, conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM produtos_unificados WHERE lista_unificada_id = ?', (lista_unificada_id,))
    produtos = cursor.fetchall()
    
    # Converter a string JSON de origem_listas de volta para um objeto Python
    produtos_com_origem = []
    for produto in produtos:
        produto_dict = dict(produto)
        try:
            produto_dict['origem_listas'] = eval(produto_dict['origem_listas']) # Usar eval com cautela, ou json.loads
        except (SyntaxError, TypeError) as e:
            logging.error(f'Erro ao parsear origem_listas para o produto {produto['id']}: {e}')
            produto_dict['origem_listas'] = [] # Fallback para lista vazia em caso de erro
        produtos_com_origem.append(produto_dict)
    
    return produtos_com_origem

@app.route('/api/export-lista-unificada/<int:lista_id>', methods=['GET'])
@login_required
def export_lista_unificada(lista_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403

    conn = get_db_connection()
    lista = conn.execute('SELECT * FROM listas_unificadas WHERE id = ?', (lista_id,)).fetchone()
    produtos = carregar_produtos_lista_unificada(lista_id, conn)
    conn.close()

    if not lista:
        return 'Lista não encontrada', 404

    # Criar um Pandas Excel writer usando BytesIO
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Aba 1: Produtos Unificados
    df_produtos = pd.DataFrame(produtos)
    if not df_produtos.empty:
        df_produtos = df_produtos[['ean', 'nome', 'cor', 'voltagem', 'modelo', 'quantidade']]
        df_produtos.columns = ['EAN', 'Nome', 'Cor', 'Voltagem', 'Modelo', 'Quantidade Total']
        df_produtos.to_excel(writer, sheet_name='Produtos Unificados', index=False)

    # Aba 2: Origem das Quantidades
    origens_data = []
    for p in produtos:
        for origem in p['origem_listas']:
            origens_data.append({
                'EAN Produto Unificado': p['ean'],
                'Nome Produto Unificado': p['nome'],
                'ID Lista Original': origem['id'],
                'Usuário Original': origem['usuario'],
                'Data Envio Original': origem['data'],
                'Quantidade Original': origem['quantidade']
            })
    df_origens = pd.DataFrame(origens_data)
    if not df_origens.empty:
        df_origens.to_excel(writer, sheet_name='Origem das Quantidades', index=False)

    # Aba 3: Informações da Lista
    info_lista = {
        'Nome da Lista Unificada': [lista['nome_lista']],
        'Responsável pela Validação': [lista['responsavel_validacao']],
        'Data de Criação': [lista['data_criacao']],
        'Total de Produtos Únicos': [lista['produtos_count']],
        'Quantidade Total de Itens': [lista['total_quantidade']]
    }
    df_info = pd.DataFrame(info_lista)
    df_info.to_excel(writer, sheet_name='Informações da Lista', index=False)

    writer.close()
    output.seek(0)

    filename = f'Lista_Unificada_{lista['responsavel_validacao']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx'
    return send_from_directory(
        directory=app.config['UPLOAD_FOLDER'],
        path=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/api/search_product', methods=['GET'])
@login_required
def search_product_route():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    conn = get_db_connection()
    # Buscar produtos no banco de dados local
    local_products = conn.execute('SELECT ean, nome, cor, voltagem, modelo FROM produtos_enviados WHERE nome LIKE ? LIMIT 10', (f'%{query}%',)).fetchall()
    conn.close()

    results = []
    for p in local_products:
        results.append({
            'ean': p['ean'],
            'nome': p['nome'],
            'cor': p['cor'],
            'voltagem': p['voltagem'],
            'modelo': p['modelo']
        })
    
    # Registrar log de atividade para a consulta
    registrar_log_atividade(session['user_id'], 'consulta', None, query, None)

    return jsonify(results)

@app.route('/api/get_item_details', methods=['GET'])
@login_required
def get_item_details_route():
    ean = request.args.get('ean', '').strip()
    if not ean:
        return jsonify({'error': 'EAN não fornecido'}), 400

    conn = get_db_connection()
    product = conn.execute('SELECT ean, nome, cor, voltagem, modelo FROM produtos_enviados WHERE ean = ?', (ean,)).fetchone()
    conn.close()

    if product:
        return jsonify({
            'ean': product['ean'],
            'nome': product['nome'],
            'cor': product['cor'],
            'voltagem': product['voltagem'],
            'modelo': product['modelo']
        })
    else:
        return jsonify({'error': 'Produto não encontrado'}), 404

@app.route('/admin/monitoramento-usuarios')
@login_required
def monitoramento_usuarios():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    # Carregar usuários não-admin
    usuarios = carregar_usuarios_nao_admin(conn)
    
    # Obter estatísticas para cada usuário
    usuarios_com_estatisticas = []
    for user in usuarios:
        stats = obter_estatisticas_usuario(user['id'], start_date_str, end_date_str, conn)
        user_dict = dict(user)
        user_dict.update(stats)
        usuarios_com_estatisticas.append(user_dict)

    conn.close()
    return render_template('monitoramento_usuarios.html', usuarios=usuarios_com_estatisticas, start_date=start_date_str, end_date=end_date_str)

def carregar_usuarios_nao_admin(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE is_admin = FALSE')
    return cursor.fetchall()

def obter_estatisticas_usuario(usuario_id, start_date_str, end_date_str, conn):
    query_base = 'SELECT COUNT(*) FROM logs_atividade WHERE usuario_id = ? AND tipo_atividade = ?'
    query_sum_qty = 'SELECT SUM(quantidade) FROM logs_atividade WHERE usuario_id = ? AND tipo_atividade = ? AND quantidade IS NOT NULL'
    query_unique_products = 'SELECT COUNT(DISTINCT ean) FROM logs_atividade WHERE usuario_id = ? AND tipo_atividade = ? AND ean IS NOT NULL'
    
    params_base = [usuario_id]
    params_sum_qty = [usuario_id]
    params_unique_products = [usuario_id]

    if start_date_str:
        query_base += ' AND data_atividade >= ?'
        query_sum_qty += ' AND data_atividade >= ?'
        query_unique_products += ' AND data_atividade >= ?'
        params_base.append(start_date_str + ' 00:00:00')
        params_sum_qty.append(start_date_str + ' 00:00:00')
        params_unique_products.append(start_date_str + ' 00:00:00')

    if end_date_str:
        query_base += ' AND data_atividade <= ?'
        query_sum_qty += ' AND data_atividade <= ?'
        query_unique_products += ' AND data_atividade <= ?'
        params_base.append(end_date_str + ' 23:59:59')
        params_sum_qty.append(end_date_str + ' 23:59:59')
        params_unique_products.append(end_date_str + ' 23:59:59')

    # Total de consultas
    total_consultas = conn.execute(query_base, params_base + ['consulta']).fetchone()[0]
    
    # Produtos únicos consultados
    produtos_unicos_consultados = conn.execute(query_unique_products, params_unique_products + ['consulta']).fetchone()[0]

    # Total de envios
    total_envios = conn.execute(query_base, params_base + ['envio']).fetchone()[0]
    
    # Total de produtos enviados (soma das quantidades)
    total_produtos_enviados = conn.execute(query_sum_qty, params_sum_qty + ['envio']).fetchone()[0]
    if total_produtos_enviados is None:
        total_produtos_enviados = 0

    return {
        'total_consultas': total_consultas,
        'produtos_unicos_consultados': produtos_unicos_consultados,
        'total_envios': total_envios,
        'total_produtos_enviados': total_produtos_enviados
    }

def registrar_log_atividade(usuario_id, tipo_atividade, ean=None, nome_produto=None, quantidade=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    data_atividade = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        'INSERT INTO logs_atividade (usuario_id, tipo_atividade, ean, nome_produto, quantidade, data_atividade) VALUES (?, ?, ?, ?, ?, ?)',
    (usuario_id, tipo_atividade, ean, nome_produto, quantidade, data_atividade))
    conn.commit()
    conn.close()
    logging.info(f'Log de atividade registrado: Usuário {usuario_id}, Tipo: {tipo_atividade}, EAN: {ean}, Nome: {nome_produto}, Qtd: {quantidade}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

