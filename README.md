# Sistema de Controle de Garantia

Um sistema web de página única para geração e controle de códigos de garantia aleatórios com impressão de etiquetas.

## Estrutura do Projeto

```
sistema_garantia/
├── src/
│   ├── main.py                 # Aplicação Flask principal
│   ├── requirements.txt         # Dependências do projeto
│   ├── Procfile                # Configuração para o Render
│   ├── .gitignore              # Arquivos a ignorar no Git
│   ├── README.md               # Documentação do projeto
│   ├── schema.sql              # Script SQL para criar a tabela
│   └── templates/
│       ├── index.html          # Página principal
│       └── login.html          # Página de login
└── README.md                   # Este arquivo
```

## Funcionalidades

- **Geração de Códigos Aleatórios**: Cria códigos únicos para controle de garantia
- **Impressão de Etiquetas**: Gera etiquetas com código de barras para impressoras Brother QL-800
- **Registro de Informações**: Armazena data da venda, nome do cliente e descrição do produto
- **Histórico Minimizado**: Visualiza e gerencia todos os códigos gerados
- **Autenticação**: Sistema de login integrado com o banco de dados existente

## Instalação e Configuração

### Localmente

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd sistema_garantia
```

2. Navegue para a pasta src:
```bash
cd src
```

3. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Configure as variáveis de ambiente:
```bash
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/seu_banco"
export FLASK_SECRET_KEY="sua_chave_secreta"
```

6. Execute a aplicação:
```bash
python main.py
```

A aplicação estará disponível em `http://localhost:5000`

### No Render

1. **Criar um novo Web Service no Render**:
   - Conecte seu repositório GitHub
   - Selecione a branch principal

2. **Configurar as variáveis de ambiente**:
   - `DATABASE_URL`: URL de conexão com o PostgreSQL
   - `FLASK_SECRET_KEY`: Chave secreta para sessões
   - `PORT`: 5000 (opcional)

3. **Configurar o comando de build**:
   ```
   cd src && pip install -r requirements.txt
   ```

4. **Configurar o comando de start**:
   ```
   cd src && python main.py
   ```

## Banco de Dados

Antes de fazer o deploy, execute o script SQL no seu banco de dados PostgreSQL:

```bash
psql -U seu_usuario -d seu_banco -f src/schema.sql
```

## Variáveis de Ambiente

### DATABASE_URL
Formato: `postgresql://[usuario]:[senha]@[host]:[porta]/[banco]`

Exemplo:
```
postgresql://admin:senha123@db.exemplo.com:5432/garantia_db
```

### FLASK_SECRET_KEY
Gere uma chave segura. Você pode usar:

```python
import secrets
print(secrets.token_hex(32))
```

## API Endpoints

### Autenticação
- `POST /login` - Login do usuário
- `GET /logout` - Logout do usuário

### Códigos de Garantia
- `POST /api/gerar-codigo` - Gera um novo código
- `GET /api/codigos` - Lista todos os códigos do usuário
- `POST /api/marcar-impressao/<id>` - Marca um código como impresso
- `DELETE /api/deletar-codigo/<id>` - Deleta um código
- `POST /api/limpar-historico` - Limpa todo o histórico

## Estrutura do Banco de Dados

### Tabela: `codigos_garantia`

```sql
CREATE TABLE codigos_garantia (
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
```

## Uso

1. **Acesse o sistema**: Faça login com suas credenciais
2. **Preencha o formulário**: Descrição do produto, data da venda e nome do cliente
3. **Gere o código**: Clique em "Gerar Código"
4. **Visualize a etiqueta**: Pré-visualize antes de imprimir
5. **Imprima**: Clique em "Imprimir Etiqueta"
6. **Histórico**: Acesse o histórico minimizado para gerenciar códigos anteriores

## Troubleshooting

### Erro: "DATABASE_URL not defined"
- Verifique se a variável de ambiente está configurada
- Reinicie a aplicação após adicionar a variável

### Erro: "Connection refused"
- Verifique se o banco de dados está acessível
- Confirme a URL de conexão
- Verifique as credenciais

### Erro: "Table does not exist"
- Execute o script SQL no banco de dados
- Verifique se o usuário tem permissão para criar tabelas

## Suporte

Para questões ou problemas, entre em contato com o time de desenvolvimento.
