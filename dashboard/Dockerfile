FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Copiar arquivos necessários
COPY requirements.txt .
COPY pages/ ./pages/
COPY components/ ./components/
COPY utils/ ./utils/
COPY Home.py .
COPY prompt/ ./prompt/
COPY .streamlit/ ./.streamlit/

# Instalar dependências
RUN pip install -r requirements.txt

# Expor porta
EXPOSE 8501

# Configurar Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comando para iniciar o Streamlit
CMD ["streamlit", "run", "Home.py"]
