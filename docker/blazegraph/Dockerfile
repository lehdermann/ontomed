FROM tomcat:9-jdk8-openjdk

# Metadados
LABEL maintainer="HMARL+GenAI Team"
LABEL description="Blazegraph database server for HMARL+GenAI system"
LABEL version="1.0"

# Variáveis de ambiente
ENV BLAZEGRAPH_VERSION=2.1.5
ENV BLAZEGRAPH_RW_PATH=/data
ENV JAVA_OPTS="-Xms1g -Xmx2g -XX:+UseG1GC -Djava.security.egd=file:/dev/./urandom \
    -Djdk.tls.ephemeralDHKeySize=2048 -Djava.awt.headless=true \
    -Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8 \
    -XX:+UseContainerSupport -XX:+UnlockExperimentalVMOptions"

# Diretório padrão do Tomcat (garantido pela imagem base)
ENV CATALINA_HOME=/usr/local/tomcat

# Criar diretório para dados persistentes
#RUN mkdir -p ${BLAZEGRAPH_RW_PATH}

# Baixar e instalar Blazegraph
RUN apt-get update && \
    apt-get install -y wget curl && \
    wget https://downloads.sourceforge.net/project/bigdata/bigdata/${BLAZEGRAPH_VERSION}/blazegraph.war \
         -O ${CATALINA_HOME}/webapps/bigdata.war && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar os arquivos de configuração (feita via volume no docker-compose)
# Mas garantimos que o diretório de destino exista
RUN mkdir -p ${CATALINA_HOME}/conf \
    && mkdir -p ${CATALINA_HOME}/bin

# Expor a porta 8080 (padrão do Tomcat)
EXPOSE 8080

# Volume para persistência de dados
VOLUME ${BLAZEGRAPH_RW_PATH}

# Comando para iniciar o Tomcat com nosso script customizado
CMD ["sh", "-c", "${CATALINA_HOME}/bin/startup.sh"]
