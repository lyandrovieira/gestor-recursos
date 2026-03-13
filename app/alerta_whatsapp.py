import os
import sqlite3
import pandas as pd
import requests
import datetime

# CONFIGURAÇÃO DE CAMINHOS ABSOLUTOS (DENTRO DO CONTAINER)
# Alinhado com o mapeamento - ./data:/data do docker-compose.yml
DB_FILE = "/data/db/gestor.db"
UPLOAD_BASE_DIR = "/data/uploads"
N8N_WEBHOOK_URL = "https://uncharacteristically-leptoprosopic-marhta.ngrok-free.dev/webhook/alerta-gestor"

def definir_status_visual(row):
    # CORREÇÃO DO ERRO DE ATTRIBUTEERROR:
    hoje = datetime.date.today() 
    
    try:
        # Garante que a data seja lida corretamente do SQLite
        prazo = datetime.datetime.strptime(row['data_limite'], '%Y-%m-%d').date()
    except Exception as e:
        return "⚠️ Erro Data", 0, 0, 1
        
    dias = (prazo - hoje).days
    
    # Contagem física usando o caminho absoluto /data/uploads
    pasta = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
    qtd_atual = 0
    if os.path.exists(pasta):
        qtd_atual = len([f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))])
    
    qtd_nec = row.get('qtd_necessaria', 1) # Evita KeyError se a coluna faltar
    qtd_percent = (qtd_atual / qtd_nec * 100) if qtd_nec > 0 else 100

    # Lógica de Urgência
    if dias > 10:
        return "🟢 Em Dia", dias, qtd_atual, qtd_nec
    elif 5 <= dias <= 10:
        status = "🟢 Em Dia" if qtd_percent >= 80 else "🟡 Atenção" if qtd_percent >= 50 else "🟠 Urgente"
        return status, dias, qtd_atual, qtd_nec
    elif 0 <= dias < 5:
        status = "🟢 Em Dia" if qtd_percent >= 90 else "🟡 Atenção" if qtd_percent >= 70 else "🟠 Urgente"
        return status, dias, qtd_atual, qtd_nec
    else:
        return "🔴 Em Atraso", dias, qtd_atual, qtd_nec

def processar_alerta():
    print(f"Buscando banco em: {DB_FILE}") # Log de verificação
    
    if not os.path.exists(DB_FILE):
        print("ERRO: Arquivo de banco de dados não encontrado!")
        return

    conn = sqlite3.connect(DB_FILE)
    # Seleciona recursos não concluídos.
    df = pd.read_sql_query("SELECT * FROM recursos WHERE concluido = 0", conn)
    conn.close()

    print(f"Recursos encontrados no banco: {len(df)}")

    if df.empty:
        # Envia para o n8n, mesmo vazio, para confirmar que o script rodou.
        requests.post(N8N_WEBHOOK_URL, json={"recursos": [], "data_relatorio": "Vazio"})
        return

    relatorio = []
    for _, row in df.iterrows():
        status, dias, atual, nec = definir_status_visual(row)
        relatorio.append({
            "nome": row['nome'],
            "status_formatado": status,
            "dias_label": "dias de atraso" if dias < 0 else "dias restantes",
            "dias_valor": abs(dias),
            "docs": f"{atual}/{nec}"
        })

    payload = {
        "data_relatorio": datetime.date.today().strftime("%d/%m/%Y"),
        "recursos": relatorio
    }
    
    requests.post(N8N_WEBHOOK_URL, json=payload)
    print("Dados enviados com sucesso!")

if __name__ == "__main__":
    processar_alerta()