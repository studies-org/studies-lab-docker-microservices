#!/bin/bash
# Roda uma vez, na primeira subida do MySQL (volume vazio).
# Cria um banco e um usuário para cada microserviço: um serviço não enxerga o banco do outro.
set -euo pipefail

for svc in items lojas pagamentos pedidos; do
  var="${svc^^}_DB_PASSWORD"
  senha="${!var:?defina ${var} no .env}"
  echo "criando ${svc}_db e ${svc}_user"
  mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${svc}_db\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${svc}_user'@'%' IDENTIFIED BY '${senha}';
GRANT ALL PRIVILEGES ON \`${svc}_db\`.* TO '${svc}_user'@'%';
SQL
done
