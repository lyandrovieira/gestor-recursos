import sqlite3
import os

# Caminho absoluto dentro do container
DB_PATH = "/app/data/db/gestor.db"

def init_db():
    # Cria a pasta db dentro de /app/data se ela não existir
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Conecta ao banco (se não existir, o SQLite cria o arquivo .db automaticamente)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cria a tabela inicial para o seu Módulo de Entrada
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        valor REAL NOT NULL,
        data_limite TEXT NOT NULL,
        documento_path TEXT,
        status TEXT DEFAULT 'Pendente'
    )
''')
    
    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")