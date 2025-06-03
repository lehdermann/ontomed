#!/bin/bash
set -e

: "${CATALINA_HOME:=/usr/local/tomcat}"

# 1) If not already extracted, unzip the WAR file
if [ ! -f "${CATALINA_HOME}/webapps/bigdata/WEB-INF/web.xml" ]; then
  echo "Extracting bigdata.war..."
  mkdir -p "${CATALINA_HOME}/webapps/bigdata"
  cd "${CATALINA_HOME}/webapps/bigdata"
  jar -xf "${CATALINA_HOME}/webapps/bigdata.war"
fi

# 2) Copy properties
echo "Copying blazegraph.properties..."
mkdir -p "${CATALINA_HOME}/webapps/bigdata/WEB-INF/classes"
cp "${CATALINA_HOME}/conf/blazegraph.properties" \
   "${CATALINA_HOME}/webapps/bigdata/WEB-INF/classes/"

# 3) Run Tomcat in foreground
echo "Starting Tomcat in foreground..."
exec "${CATALINA_HOME}/bin/catalina.sh" run
