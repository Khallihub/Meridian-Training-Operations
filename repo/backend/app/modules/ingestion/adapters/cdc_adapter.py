"""CDC adapters for MySQL (binlog) and PostgreSQL (logical replication)."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def test_mysql_connectivity(config: dict) -> tuple[bool, float | None, str | None]:
    try:
        import mysql.connector
        t0 = time.monotonic()
        conn = mysql.connector.connect(
            host=config["host"],
            port=config.get("port", 3306),
            user=config["user"],
            password=config["password"],
            database=config.get("database", ""),
            connection_timeout=5,
        )
        conn.close()
        return True, round((time.monotonic() - t0) * 1000, 1), None
    except Exception as e:
        return False, None, str(e)


def test_pg_connectivity(config: dict) -> tuple[bool, float | None, str | None]:
    try:
        import psycopg2
        t0 = time.monotonic()
        conn = psycopg2.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config["user"],
            password=config["password"],
            dbname=config.get("database", ""),
            connect_timeout=5,
        )
        conn.close()
        return True, round((time.monotonic() - t0) * 1000, 1), None
    except Exception as e:
        return False, None, str(e)


def pull_mysql_cdc(config: dict, max_rows: int = 1000) -> tuple[list[dict[str, Any]], int]:
    """Pull rows via MySQL binlog position tracking."""
    try:
        from pymysqlreplication import BinLogStreamReader
        from pymysqlreplication.row_event import WriteRowsEvent, UpdateRowsEvent

        rows: list[dict] = []
        stream = BinLogStreamReader(
            connection_settings={
                "host": config["host"],
                "port": config.get("port", 3306),
                "user": config["user"],
                "passwd": config["password"],
            },
            server_id=config.get("server_id", 100),
            log_file=config.get("log_file"),
            log_pos=config.get("log_pos"),
            only_events=[WriteRowsEvent, UpdateRowsEvent],
            blocking=False,
        )
        for event in stream:
            for row in event.rows:
                rows.append(row.get("values") or row.get("after_values") or {})
                if len(rows) >= max_rows:
                    break
            if len(rows) >= max_rows:
                break
        stream.close()
        return rows, len(rows)
    except ImportError:
        logger.warning("pymysqlreplication not installed; CDC pull skipped.")
        return [], 0
    except Exception as e:
        logger.error("MySQL CDC error: %s", e)
        return [], 0


def pull_pg_cdc(config: dict, max_rows: int = 1000) -> tuple[list[dict[str, Any]], int]:
    """Pull rows via PostgreSQL logical replication slot."""
    try:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config["user"],
            password=config["password"],
            dbname=config.get("database"),
            connection_factory=psycopg2.extras.LogicalReplicationConnection,
        )
        cur = conn.cursor()
        slot = config.get("slot_name", "meridian_slot")
        rows: list[dict] = []
        cur.start_replication(slot_name=slot, decode=True)
        for msg in cur:
            rows.append({"data": msg.payload})
            msg.cursor.send_feedback(flush_lsn=msg.data_start)
            if len(rows) >= max_rows:
                break
        conn.close()
        return rows, len(rows)
    except Exception as e:
        logger.error("PG CDC error: %s", e)
        return [], 0
