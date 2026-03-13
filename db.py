import aiosqlite
from typing import Optional
import os

DB_PATH = os.getenv("DB_PATH", "qurilish_bot.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                full_name   TEXT    NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'client',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS projects (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                description  TEXT,
                master_id    INTEGER NOT NULL,
                invite_token TEXT    UNIQUE NOT NULL,
                budget_limit REAL    DEFAULT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (master_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS project_clients (
                project_id  INTEGER NOT NULL,
                client_id   INTEGER NOT NULL,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, client_id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (client_id)  REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL,
                master_id       INTEGER NOT NULL,
                material        TEXT    NOT NULL,
                amount          REAL    NOT NULL,
                receipt_file_id TEXT,
                note            TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (master_id)  REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id    INTEGER NOT NULL,
                master_id     INTEGER NOT NULL,
                text          TEXT    NOT NULL,
                photo_file_id TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (master_id)  REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                sender_id   INTEGER NOT NULL,
                sender_name TEXT    NOT NULL,
                sender_role TEXT    NOT NULL,
                text        TEXT    NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
        """)
        await db.commit()

async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def create_user(user_id: int, full_name: str, role: str = "client"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id, full_name, role) VALUES (?, ?, ?)", (user_id, full_name, role))
        await db.commit()

async def set_user_role(user_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        await db.commit()

async def create_project(name: str, description: str, master_id: int, token: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO projects (name, description, master_id, invite_token) VALUES (?, ?, ?, ?)", (name, description, master_id, token))
        await db.commit()
        return cur.lastrowid

async def get_project_by_token(token: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE invite_token = ?", (token,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_project_by_id(project_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_master_projects(master_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE master_id = ? ORDER BY created_at DESC", (master_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def get_client_projects(client_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""SELECT p.* FROM projects p JOIN project_clients pc ON p.id = pc.project_id WHERE pc.client_id = ? ORDER BY p.created_at DESC""", (client_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def add_client_to_project(project_id: int, client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO project_clients (project_id, client_id) VALUES (?, ?)", (project_id, client_id))
        await db.commit()

async def is_client_in_project(project_id: int, client_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM project_clients WHERE project_id=? AND client_id=?", (project_id, client_id)) as cur:
            return await cur.fetchone() is not None

async def get_project_participants(project_id: int, exclude_id: int) -> list:
    project = await get_project_by_id(project_id)
    ids = {project["master_id"]}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT client_id FROM project_clients WHERE project_id = ?", (project_id,)) as cur:
            for row in await cur.fetchall():
                ids.add(row[0])
    ids.discard(exclude_id)
    return list(ids)

async def add_expense(project_id: int, master_id: int, material: str, amount: float, receipt_file_id=None, note=None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO expenses (project_id, master_id, material, amount, receipt_file_id, note) VALUES (?, ?, ?, ?, ?, ?)", (project_id, master_id, material, amount, receipt_file_id, note))
        await db.commit()
        return cur.lastrowid

async def get_project_expenses(project_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM expenses WHERE project_id = ? ORDER BY created_at DESC", (project_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def get_total_expenses(project_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE project_id = ?", (project_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0

async def get_expenses_since(project_id: int, since_date: str) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE project_id = ? AND date(created_at) >= ?", (project_id, since_date)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0

async def get_top_materials(project_id: int, limit: int = 5) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT material, SUM(amount) as total FROM expenses WHERE project_id = ? GROUP BY material ORDER BY total DESC LIMIT ?", (project_id, limit)) as cur:
            return await cur.fetchall()

async def set_budget_limit(project_id: int, limit: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE projects SET budget_limit = ? WHERE id = ?", (limit, project_id))
        await db.commit()

async def get_budget_limit(project_id: int) -> Optional[float]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT budget_limit FROM projects WHERE id = ?", (project_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row and row[0] else None

async def add_report(project_id: int, master_id: int, text: str, photo_file_id=None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO reports (project_id, master_id, text, photo_file_id) VALUES (?, ?, ?, ?)", (project_id, master_id, text, photo_file_id))
        await db.commit()
        return cur.lastrowid

async def get_project_reports(project_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reports WHERE project_id = ? ORDER BY created_at DESC", (project_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def save_message(project_id: int, sender_id: int, sender_name: str, sender_role: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (project_id, sender_id, sender_name, sender_role, text) VALUES (?, ?, ?, ?, ?)", (project_id, sender_id, sender_name, sender_role, text))
        await db.commit()

async def get_project_messages(project_id: int, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM messages WHERE project_id = ? ORDER BY created_at DESC LIMIT ?", (project_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]
