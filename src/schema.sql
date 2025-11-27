-- Script SQL para criar a tabela de códigos de garantia
-- Execute este script no seu banco de dados PostgreSQL

-- Criar tabela codigos_garantia
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

-- Criar índices para otimizar consultas
CREATE INDEX IF NOT EXISTS idx_codigos_garantia_usuario 
ON codigos_garantia (usuario_id);

CREATE INDEX IF NOT EXISTS idx_codigos_garantia_codigo 
ON codigos_garantia (codigo_aleatorio);

CREATE INDEX IF NOT EXISTS idx_codigos_garantia_data_criacao 
ON codigos_garantia (data_criacao);

-- Comentários nas colunas
COMMENT ON TABLE codigos_garantia IS 'Armazena os códigos de garantia gerados pelo sistema';
COMMENT ON COLUMN codigos_garantia.codigo_aleatorio IS 'Código único gerado aleatoriamente para a garantia';
COMMENT ON COLUMN codigos_garantia.descricao_produto IS 'Descrição do produto associado ao código de garantia';
COMMENT ON COLUMN codigos_garantia.data_venda IS 'Data em que o produto foi vendido';
COMMENT ON COLUMN codigos_garantia.nome_cliente IS 'Nome do cliente que comprou o produto';
COMMENT ON COLUMN codigos_garantia.usuario_id IS 'ID do usuário que gerou o código';
COMMENT ON COLUMN codigos_garantia.data_criacao IS 'Data e hora em que o código foi criado';
COMMENT ON COLUMN codigos_garantia.data_impressao IS 'Data e hora em que o código foi impresso (NULL se não impresso)';
COMMENT ON COLUMN codigos_garantia.ativo IS 'Indica se o código está ativo (TRUE) ou deletado (FALSE)';
