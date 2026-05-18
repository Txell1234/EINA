"""Crea la base de dades MySQL si no existeix i les taules."""
import os
import pymysql
from sqlalchemy import create_engine, text
from database import engine, Base
from models import Case, OSINTData, AIAnalysis, RiskConcept, RiskAnalysis, KPI, QualitativeAnalysis, UnifiedAnalysis, InvestmentRecommendation

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "osint")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "osint")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "osint")
USE_MYSQL = os.getenv("USE_MYSQL", "1").lower() in ("1", "true", "yes")


def init_mysql():
    """Crea la base de dades si no existeix."""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"AVÍS: No s'ha pogut connectar a MySQL: {e}")
        print("Comprova que MySQL estigui en marxa i que MYSQL_USER/MYSQL_PASSWORD siguin correctes.")
        print("O usa USE_MYSQL=0 per SQLite.")
        raise


def main():
    if USE_MYSQL:
        init_mysql()
    Base.metadata.create_all(bind=engine)
    db_type = "MySQL" if USE_MYSQL else "SQLite"
    print(f"Base de dades ({db_type}) i taules creades correctament.")


if __name__ == "__main__":
    main()
