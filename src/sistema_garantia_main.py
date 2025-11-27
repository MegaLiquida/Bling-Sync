import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime
import secrets
import string
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "garantia_app_secret_key_default")

# Configuração do banco de dados
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("Erro: Variável de ambiente DATABASE_URL não definida.")
    sys.exit(1)

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_database():
    """Inicializa as tabelas necessárias para o sistema de garantia"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Tabela para armazenar códigos de garantia gerados
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS codigos_garantia (
                    id SERIAL PRIMARY KEY,
                    codigo_aleatorio TEXT NOT NULL UNIQUE,
                    descricao_produto TEXT NOT NULL,
                    data_venda DATE NOT NULL,
                    nome_cliente TEXT NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_impressao TIMESTAMP,
                    ativo BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                );
                """)
                
                # Criar índices para otimizar consultas
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_codigos_garantia_usuario 
                ON codigos_garantia (usuario_id);
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_codigos_garantia_codigo 
                ON codigos_garantia (codigo_aleatorio);
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_codigos_garantia_data_criacao 
                ON codigos_garantia (data_criacao);
                """)
                
                conn.commit()
                print("Banco de dados inicializado com sucesso para o sistema de garantia.")
    except psycopg2.Error as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

def gerar_codigo_aleatorio(tamanho=12):
    """Gera um código aleatório único para a garantia"""
    caracteres = string.ascii_uppercase + string.digits
    while True:
        codigo = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
        # Verificar se o código já existe
        if not codigo_existe(codigo):
            return codigo

def codigo_existe(codigo):
    """Verifica se um código já existe no banco de dados"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM codigos_garantia WHERE codigo_aleatorio = %s", (codigo,))
                return cursor.fetchone() is not None
    except psycopg2.Error as e:
        print(f"Erro ao verificar código: {e}")
        return False

def obter_nome_usuario(usuario_id):
    """Obtém o nome do usuário pelo ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (usuario_id,))
                resultado = cursor.fetchone()
                return resultado[0] if resultado else None
    except psycopg2.Error as e:
        print(f"Erro ao obter nome do usuário: {e}")
        return None

def verificar_usuario(nome, senha):
    """Verifica as credenciais do usuário"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT id, senha_hash FROM usuarios WHERE nome = %s", (nome,))
                usuario = cursor.fetchone()
        
        if usuario and check_password_hash(usuario["senha_hash"], senha):
            return {"id": usuario["id"]}
        return None
    except psycopg2.Error as e:
        print(f"Erro ao verificar usuário: {e}")
        return None

# ============================================================================
# ROTAS
# ============================================================================

@app.route("/")
def index():
    """Página principal do sistema"""
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    
    usuario_nome = obter_nome_usuario(session["usuario_id"])
    return render_template("index.html", usuario_nome=usuario_nome)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Rota de login"""
    if request.method == "POST":
        data = request.get_json()
        nome = data.get("nome")
        senha = data.get("senha")
        
        usuario = verificar_usuario(nome, senha)
        if usuario:
            session["usuario_id"] = usuario["id"]
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "message": "Usuário ou senha inválidos"}), 401
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Rota de logout"""
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/gerar-codigo", methods=["POST"])
def gerar_codigo():
    """API para gerar um novo código de garantia"""
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        data = request.get_json()
        descricao_produto = data.get("descricao_produto", "").strip()
        data_venda = data.get("data_venda", "").strip()
        nome_cliente = data.get("nome_cliente", "").strip()
        
        # Validações
        if not descricao_produto or len(descricao_produto) < 3:
            return jsonify({"error": "Descrição do produto deve ter pelo menos 3 caracteres"}), 400
        
        if not data_venda:
            return jsonify({"error": "Data da venda é obrigatória"}), 400
        
        if not nome_cliente or len(nome_cliente) < 3:
            return jsonify({"error": "Nome do cliente deve ter pelo menos 3 caracteres"}), 400
        
        # Gerar código aleatório
        codigo_aleatorio = gerar_codigo_aleatorio()
        
        # Salvar no banco de dados
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                INSERT INTO codigos_garantia 
                (codigo_aleatorio, descricao_produto, data_venda, nome_cliente, usuario_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """, (codigo_aleatorio, descricao_produto, data_venda, nome_cliente, session["usuario_id"]))
                
                codigo_id = cursor.fetchone()[0]
                conn.commit()
        
        return jsonify({
            "success": True,
            "codigo": codigo_aleatorio,
            "id": codigo_id,
            "descricao_produto": descricao_produto,
            "data_venda": data_venda,
            "nome_cliente": nome_cliente
        }), 200
    
    except Exception as e:
        print(f"Erro ao gerar código: {e}")
        return jsonify({"error": f"Erro ao processar requisição: {str(e)}"}), 500

@app.route("/api/codigos", methods=["GET"])
def obter_codigos():
    """API para obter todos os códigos gerados pelo usuário"""
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                SELECT id, codigo_aleatorio, descricao_produto, data_venda, nome_cliente, 
                       data_criacao, data_impressao
                FROM codigos_garantia
                WHERE usuario_id = %s AND ativo = TRUE
                ORDER BY data_criacao DESC
                """, (session["usuario_id"],))
                
                codigos = [dict(row) for row in cursor.fetchall()]
        
        return jsonify(codigos), 200
    
    except Exception as e:
        print(f"Erro ao obter códigos: {e}")
        return jsonify({"error": f"Erro ao processar requisição: {str(e)}"}), 500

@app.route("/api/marcar-impressao/<int:codigo_id>", methods=["POST"])
def marcar_impressao(codigo_id):
    """API para marcar um código como impresso"""
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                UPDATE codigos_garantia
                SET data_impressao = %s
                WHERE id = %s AND usuario_id = %s
                """, (datetime.now(), codigo_id, session["usuario_id"]))
                
                conn.commit()
        
        return jsonify({"success": True}), 200
    
    except Exception as e:
        print(f"Erro ao marcar impressão: {e}")
        return jsonify({"error": f"Erro ao processar requisição: {str(e)}"}), 500

@app.route("/api/deletar-codigo/<int:codigo_id>", methods=["DELETE"])
def deletar_codigo(codigo_id):
    """API para deletar um código de garantia"""
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                UPDATE codigos_garantia
                SET ativo = FALSE
                WHERE id = %s AND usuario_id = %s
                """, (codigo_id, session["usuario_id"]))
                
                conn.commit()
        
        return jsonify({"success": True}), 200
    
    except Exception as e:
        print(f"Erro ao deletar código: {e}")
        return jsonify({"error": f"Erro ao processar requisição: {str(e)}"}), 500

@app.route("/api/limpar-historico", methods=["POST"])
def limpar_historico():
    """API para limpar todo o histórico de códigos do usuário"""
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                UPDATE codigos_garantia
                SET ativo = FALSE
                WHERE usuario_id = %s
                """, (session["usuario_id"],))
                
                conn.commit()
        
        return jsonify({"success": True}), 200
    
    except Exception as e:
        print(f"Erro ao limpar histórico: {e}")
        return jsonify({"error": f"Erro ao processar requisição: {str(e)}"}), 500

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    init_database()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
