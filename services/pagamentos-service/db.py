"""Acesso ao MySQL do serviço (cada serviço tem o próprio banco e usuário)."""
import os
import time
from contextlib import contextmanager
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor


def connect(autocommit=True):
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=autocommit,
        connect_timeout=5,
    )


def _plain(row):
    """Converte Decimal e datas para tipos que o jsonify entende bem."""
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            v = float(v)
        elif hasattr(v, "isoformat"):
            v = v.isoformat()
        out[k] = v
    return out


def query(sql, args=None):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return [_plain(r) for r in cur.fetchall()]


def query_one(sql, args=None):
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql, args=None):
    """Executa um comando e devolve (lastrowid, rowcount)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.lastrowid, cur.rowcount


@contextmanager
def transaction():
    conn = connect(autocommit=False)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(statements, retries=30, wait=2):
    """Cria as tabelas na subida, esperando o MySQL ficar pronto."""
    for attempt in range(1, retries + 1):
        try:
            with connect() as conn, conn.cursor() as cur:
                for sql in statements:
                    cur.execute(sql)
            return
        except pymysql.err.OperationalError:
            if attempt == retries:
                raise
            time.sleep(wait)


def healthy():
    try:
        query("SELECT 1 AS ok")
        return True
    except Exception:
        return False
