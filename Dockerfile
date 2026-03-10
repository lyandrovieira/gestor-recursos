# Imagem leve baseada em Debian
FROM python:3.11-slim-bookworm

# Evita que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema para SQLite e ferramentas básicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python
# Criaremos o requirements.txt na próxima etapa, por ora:
RUN pip install --no-cache-dir streamlit pandas

# Expõe a porta padrão do Streamlit
EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]