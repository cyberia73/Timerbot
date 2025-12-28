import sqlite3
from dataclasses import dataclass
from typing import Optional, List
import os

DB_PATH = os.getenv("DB_PATH", "/data/bot.db")

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            guild_id INTEGER,
            channel_id INTEGER,
            job TEXT,
            user_id INTEGER,
            PRIMARY KEY (guild_id, channel_id, job, user_id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS steel (
            guild_id INTEGER,
            channel_id INTEGER,
            active INTEGER,
            start_ts INTEGER,
            last_refuel_ts INTEGER,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS silk (
            guild_id INTEGER,
            channel_id INTEGER,
            stage TEXT,
            start_ts INTEGER,
            ack_stage TEXT,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)
        con.commit()

# =====================
# 대상자 관리
# =====================
def add_targets(g, c, job, users: List[int]):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for u in users:
            cur.execute(
                "INSERT OR IGNORE INTO targets VALUES (?,?,?,?)",
                (g, c, job, u)
            )
        con.commit()

def remove_targets(g, c, job, users: List[int]):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for u in users:
            cur.execute(
                "DELETE FROM targets WHERE guild_id=? AND channel_id=? AND job=? AND user_id=?",
                (g, c, job, u)
            )
        con.commit()

def get_targets(g, c, job) -> List[int]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT user_id FROM targets WHERE guild_id=? AND channel_id=? AND job=?",
            (g, c, job)
        )
        return [r[0] for r in cur.fetchall()]

# =====================
# 강철
# =====================
@dataclass(slots=True)
class SteelState:
    active: bool
    start_ts: Optional[int]
    last_refuel_ts: Optional[int]

def get_steel(g, c) -> SteelState:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT active,start_ts,last_refuel_ts FROM steel WHERE guild_id=? AND channel_id=?",
            (g, c)
        )
        r = cur.fetchone()
    if not r:
        return SteelState(False, None, None)
    return SteelState(bool(r[0]), r[1], r[2])

def set_steel(g, c, s: SteelState):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO steel VALUES (?,?,?,?,?)
        ON CONFLICT(guild_id,channel_id) DO UPDATE SET
            active=excluded.active,
            start_ts=excluded.start_ts,
            last_refuel_ts=excluded.last_refuel_ts
        """, (g, c, int(s.active), s.start_ts, s.last_refuel_ts))
        con.commit()

# =====================
# 양잠
# =====================
@dataclass(slots=True)
class SilkState:
    stage: str
    start_ts: Optional[int]
    ack_stage: Optional[str]

def get_silk(g, c) -> SilkState:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT stage,start_ts,ack_stage FROM silk WHERE guild_id=? AND channel_id=?",
            (g, c)
        )
        r = cur.fetchone()
    if not r:
        return SilkState("none", None, None)
    return SilkState(r[0], r[1], r[2])

def set_silk(g, c, s: SilkState):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO silk VALUES (?,?,?,?,?)
        ON CONFLICT(guild_id,channel_id) DO UPDATE SET
            stage=excluded.stage,
            start_ts=excluded.start_ts,
            ack_stage=excluded.ack_stage
        """, (g, c, s.stage, s.start_ts, s.ack_stage))
        con.commit()
