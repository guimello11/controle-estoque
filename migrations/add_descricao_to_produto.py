from sqlalchemy import create_engine, MetaData, Table, Column, String
from sqlalchemy.engine import reflection

# Conectar ao banco de dados
engine = create_engine('sqlite:///estoque.db')
metadata = MetaData()

# Verificar se a coluna já existe
inspector = reflection.Inspector.from_engine(engine)
columns = [col['name'] for col in inspector.get_columns('produto')]

if 'descricao' not in columns:
    # Adicionar a coluna descricao
    with engine.connect() as conn:
        conn.execute("ALTER TABLE produto ADD COLUMN descricao VARCHAR(200)")
        conn.commit()
        print("Coluna 'descricao' adicionada com sucesso à tabela 'produto'")
else:
    print("A coluna 'descricao' já existe na tabela 'produto'")
