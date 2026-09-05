"""Local dashboard API for Crewism.

Stdlib-only HTTP server on 127.0.0.1 (never exposed publicly).
Bearer-token auth via DASHBOARD_TOKEN. Reads/writes the same SQLite file
the bot uses (WAL mode, short transactions). Started as a daemon thread
from main.py so `npm start` can boot bot + dashboard together.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

log = logging.getLogger("crewism.dash")

_holder: dict = {"bot": None, "start_time": None}


def attach_bot(bot, start_time):
    _holder["bot"] = bot
    _holder["start_time"] = start_time


def _db_path() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///crewism.db")
    if url.startswith("sqlite"):
        return url.split("///")[-1].split("?")[0]
    raise RuntimeError("dashboard API only supports sqlite")


def _connect():
    con = sqlite3.connect(_db_path(), timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _get(path: str):
    return json.loads(path) if path else {}


DEFAULT_SERVER = {
    "encounter_enabled": 1, "pvp_enabled": 1, "gambling_enabled": 1,
    "spawn_channel": None, "config": {},
}


def q_overview(guild_id: int | None = None):
    out: dict = {}
    with _connect() as con:
        g = "WHERE guild_id = ?" if guild_id else ""
        args = (guild_id,) if guild_id else ()
        out["players"] = con.execute(f"SELECT COUNT(*) c FROM players {g}", args).fetchone()["c"]
        out["money_supply"] = con.execute(f"SELECT COALESCE(SUM(money),0) s FROM players {g}", args).fetchone()["s"]
        out["characters"] = con.execute(
            "SELECT COUNT(*) c FROM char_instances" + (f" {g}" if guild_id else ""), args).fetchone()["c"]
        out["crews"] = con.execute(
            "SELECT COUNT(*) c FROM crews" + (f" {g}" if guild_id else ""), args).fetchone()["c"]
        out["battles_7d"] = con.execute(
            "SELECT COUNT(*) c FROM battles WHERE created_at > datetime('now','-7 days')"
            + (" AND guild_id = ?" if guild_id else ""), ((guild_id,) if guild_id else ())).fetchone()["c"]
        out["territories_held"] = 0
        if guild_id:
            out["territories_held"] = con.execute(
                "SELECT COUNT(*) c FROM territory_ownership WHERE guild_id = ? AND owner_type != 'npc'",
                (guild_id,)).fetchone()["c"]
    bot = _holder["bot"]
    out["guilds_live"] = len(bot.guilds) if bot else 0
    return out


def q_players(guild_id: int | None, sort: str, limit: int):
    col = {"wins": "wins", "money": "money", "bounty": "bounty", "level": "level"}.get(sort, "wins")
    with _connect() as con:
        if guild_id:
            rows = con.execute(
                f"SELECT user_id,name,level,xp,money,reputation,wins,losses,bounty,region FROM players "
                f"WHERE guild_id=? ORDER BY {col} DESC LIMIT ?", (guild_id, limit)).fetchall()
        else:
            rows = con.execute(
                f"SELECT guild_id,user_id,name,level,money,wins,bounty FROM players "
                f"ORDER BY {col} DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def q_ledger(guild_id: int | None, limit: int = 25):
    with _connect() as con:
        if guild_id:
            rows = con.execute(
                "SELECT user_id,amount,before,\"after\",reason,ref,created_at FROM economy_ledger "
                "WHERE guild_id=? ORDER BY id DESC LIMIT ?", (guild_id, limit)).fetchall()
        else:
            rows = con.execute(
                "SELECT guild_id,user_id,amount,reason,created_at FROM economy_ledger "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def q_bosses():
    with _connect() as con:
        bosses = [dict(r) for r in con.execute("SELECT id,name,level,region,cooldown_h FROM bosses").fetchall()]
        for b in bosses:
            b["fights_7d"] = con.execute(
                "SELECT COUNT(*) c FROM boss_attempts WHERE boss_id=? AND attempted_at > datetime('now','-7 days')",
                (b["id"],)).fetchone()["c"]
            b["kills_7d"] = con.execute(
                "SELECT COUNT(*) c FROM boss_attempts WHERE boss_id=? AND won=1 AND attempted_at > datetime('now','-7 days')",
                (b["id"],)).fetchone()["c"]
    return bosses


def q_territories(guild_id: int | None):
    with _connect() as con:
        terrs = [dict(r) for r in con.execute("SELECT id,name,rec_level,income FROM territories").fetchall()]
        if guild_id:
            for t in terrs:
                o = con.execute("SELECT owner_type,crew_id FROM territory_ownership WHERE guild_id=? AND territory_id=?",
                                (guild_id, t["id"])).fetchone()
                t["owner_type"] = o["owner_type"] if o else "npc"
                t["crew_id"] = o["crew_id"] if o else None
                if t["crew_id"]:
                    c = con.execute("SELECT name FROM crews WHERE id=?", (t["crew_id"],)).fetchone()
                    t["crew_name"] = c["name"] if c else None
    return terrs


def q_events():
    with _connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT id,name,starts_at,ends_at,active FROM events ORDER BY active DESC").fetchall()]


def q_server(gid: int) -> dict:
    with _connect() as con:
        r = con.execute("SELECT encounter_enabled,pvp_enabled,gambling_enabled,spawn_channel,config "
                        "FROM server_config WHERE guild_id=?", (gid,)).fetchone()
        if not r:
            return {"guild_id": gid, **DEFAULT_SERVER}
        d = dict(r)
        d["guild_id"] = gid
        d["config"] = _get(d.get("config") or "{}")
        return d


def save_server(gid: int, data: dict) -> dict:
    cur = q_server(gid)
    for k in ("encounter_enabled", "pvp_enabled", "gambling_enabled"):
        if k in data:
            cur[k] = 1 if data[k] else 0
    if "spawn_channel" in data:
        cur["spawn_channel"] = int(data["spawn_channel"]) if data["spawn_channel"] else None
    if "config" in data and isinstance(data["config"], dict):
        merged = dict(cur.get("config") or {})
        merged.update(data["config"])
        cur["config"] = merged
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO server_config (guild_id,encounter_enabled,pvp_enabled,gambling_enabled,spawn_channel,config)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(guild_id) DO UPDATE SET encounter_enabled=excluded.encounter_enabled,"
            " pvp_enabled=excluded.pvp_enabled, gambling_enabled=excluded.gambling_enabled,"
            " spawn_channel=excluded.spawn_channel, config=excluded.config",
            (gid, cur["encounter_enabled"], cur["pvp_enabled"], cur["gambling_enabled"],
             cur["spawn_channel"], json.dumps(cur["config"])))
        con.commit()
    return q_server(gid)


def save_event(event_id: str, active: bool):
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE events SET active=? WHERE id=?", (1 if active else 0, event_id))
        con.commit()
    return {"id": event_id, "active": bool(active)}


class Handler(BaseHTTPRequestHandler):
    server_version = "CrewismDash/1.0"

    def log_message(self, *a):
        pass

    def _auth(self) -> bool:
        token = os.getenv("DASHBOARD_TOKEN", "")
        if not token:
            return False
        return self.headers.get("Authorization") == f"Bearer {token}"

    def _send(self, code: int, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, OSError):
            return {}

    def do_GET(self):
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        gid = int(qs["guild_id"][0]) if qs.get("guild_id", [""])[0].isdigit() else None
        try:
            if u.path == "/api/health":
                bot = _holder["bot"]
                return self._send(200, {"ok": True,
                                        "guilds": [{"id": g.id, "name": g.name, "members": g.member_count}
                                                   for g in (bot.guilds if bot else [])]})
            if u.path == "/api/overview":
                return self._send(200, q_overview(gid))
            if u.path == "/api/players":
                return self._send(200, q_players(gid, qs.get("sort", ["wins"])[0],
                                                 min(100, int(qs.get("limit", ["25"])[0]))))
            if u.path == "/api/ledger":
                return self._send(200, q_ledger(gid))
            if u.path == "/api/bosses":
                return self._send(200, q_bosses())
            if u.path == "/api/territories":
                return self._send(200, q_territories(gid))
            if u.path == "/api/events":
                return self._send(200, q_events())
            if u.path.startswith("/api/server/"):
                return self._send(200, q_server(int(u.path.rsplit("/", 1)[1])))
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001 - API must never crash the bot
            log.warning("dash api error: %s", e)
            return self._send(500, {"error": "internal"})

    def do_POST(self):
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        u = urlparse(self.path)
        try:
            if u.path.startswith("/api/server/"):
                gid = int(u.path.rsplit("/", 1)[1])
                return self._send(200, save_server(gid, self._body()))
            if u.path.startswith("/api/events/"):
                eid = u.path.rsplit("/", 1)[1]
                return self._send(200, save_event(eid, bool(self._body().get("active"))))
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            log.warning("dash api error: %s", e)
            return self._send(500, {"error": "internal"})


def start(port: int = 3100):
    if not os.getenv("DASHBOARD_TOKEN"):
        log.warning("DASHBOARD_TOKEN not set — dashboard API disabled")
        return None
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="dash-api")
    t.start()
    log.info("dashboard API on 127.0.0.1:%d", port)
    return srv
