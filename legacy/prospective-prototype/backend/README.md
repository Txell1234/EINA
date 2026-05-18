# Backend OSINT Platform

## MySQL

1. Crea la base de dades i usuari:

```sql
CREATE DATABASE osint CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'osint'@'localhost' IDENTIFIED BY 'osint';
GRANT ALL PRIVILEGES ON osint.* TO 'osint'@'localhost';
FLUSH PRIVILEGES;
```

2. Variables d'entorn (opcional):

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=osint
export MYSQL_PASSWORD=osint
export MYSQL_DATABASE=osint
```

3. Per usar SQLite en lloc de MySQL:

```bash
export USE_MYSQL=0
```

4. Inicialitzar taules (primer cop):

```bash
python init_db.py
```

5. Executar:

```bash
python run.py
```
