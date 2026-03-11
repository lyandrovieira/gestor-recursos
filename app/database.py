import sqlite3
import os

DB_PATH = "/data/db/gestor.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Adicionada a coluna 'concluido' (0 para não, 1 para sim)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            data_limite TEXT NOT NULL,
            documento_path TEXT,
            status TEXT DEFAULT 'Pendente',
            qtd_necessaria INTEGER DEFAULT 1,
            concluido INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()