# Sistema de Controle de Garantia

Um sistema web de página única para geração e controle de códigos de garantia aleatórios com impressão de etiquetas.

## Funcionalidades

- **Geração de Códigos Aleatórios**: Cria códigos únicos para controle de garantia
- **Impressão de Etiquetas**: Gera etiquetas com código de barras para impressoras Brother QL-800
- **Registro de Informações**: Armazena data da venda, nome do cliente e descrição do produto
- **Histórico Minimizado**: Visualiza e gerencia todos os códigos gerados
- **Autenticação**: Sistema de login integrado com o banco de dados existente

## Requisitos

- Python 3.8+
- PostgreSQL
- pip

## Instalação Local

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd sistema_garantia
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/seu_banco"
export FLASK_SECRET_KEY="sua_chave_secreta"
```

5. Execute a aplicação:
```bash
python main.py
```

A aplicação estará disponível em `http://localhost:5000`

## Configuração no Render

1. **Criar um novo Web Service no Render**:
   - Conecte seu repositório GitHub
   - Selecione a branch principal

2. **Configurar as variáveis de ambiente**:
   - `DATABASE_URL`: URL de conexão com o PostgreSQL
   - `FLASK_SECRET_KEY`: Chave secreta para sessões

3. **Configurar o comando de build**:
   ```
   pip install -r requirements.txt
   ```

4. **Configurar o comando de start**:
   ```
   python main.py
   ```

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

## Uso

1. **Acesse o sistema**: Faça login com suas credenciais
2. **Preencha o formulário**: Descrição do produto, data da venda e nome do cliente
3. **Gere o código**: Clique em "Gerar Código"
4. **Visualize a etiqueta**: Pré-visualize antes de imprimir
5. **Imprima**: Clique em "Imprimir Etiqueta"
6. **Histórico**: Acesse o histórico minimizado para gerenciar códigos anteriores

## Notas Importantes

- O sistema utiliza o mesmo banco de dados PostgreSQL do sistema principal de cadastro de produtos
- Os códigos são gerados aleatoriamente e armazenados como únicos
- A impressão é otimizada para impressoras Brother QL-800 (90mm x 29mm)
- O histórico pode ser expandido/minimizado conforme necessário

## Suporte

Para questões ou problemas, entre em contato com o time de desenvolvimento.
