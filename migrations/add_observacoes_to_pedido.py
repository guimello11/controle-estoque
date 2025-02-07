from app import db

def upgrade():
    # Adiciona a coluna observacoes à tabela pedido
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE pedido ADD COLUMN observacoes TEXT')
        conn.commit()

def downgrade():
    # Remove a coluna observacoes da tabela pedido
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE pedido DROP COLUMN observacoes')
        conn.commit()

if __name__ == '__main__':
    upgrade()
