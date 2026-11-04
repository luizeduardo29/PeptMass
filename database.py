"""
database.py
===========
Persistência local em SQLite para aminoácidos personalizados e
modificações customizadas criadas pelo usuário.
"""

import os
import sqlite3
from contextlib import closing

DEFAULT_DB_PATH = os.path.join(
    os.path.expanduser("~"), ".peptmass", "peptmass.db"
)


class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # check_same_thread=False: a versao web atende cada requisicao numa
        # thread; o acesso e serializado por uma trava (web/state.py).
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with closing(self.conn.cursor()) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS custom_residues (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    name      TEXT    NOT NULL,
                    three     TEXT    NOT NULL,
                    code      TEXT    NOT NULL UNIQUE,
                    formula   TEXT    NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS custom_modifications (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL UNIQUE,
                    formula     TEXT    NOT NULL,
                    targets     TEXT    NOT NULL,
                    position    TEXT    NOT NULL,
                    description TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_peptides (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    name         TEXT    NOT NULL UNIQUE,
                    sequence     TEXT    NOT NULL,
                    n_term_mod   TEXT,
                    c_term_mod   TEXT,
                    residue_mods TEXT,
                    notes        TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()

    # ---------------- resíduos personalizados ----------------
    def add_residue(self, name, three, code, formula):
        with closing(self.conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO custom_residues (name, three, code, formula) "
                "VALUES (?,?,?,?)", (name, three, code, formula))
            self.conn.commit()
            return cur.lastrowid

    def delete_residue(self, rid):
        with closing(self.conn.cursor()) as cur:
            cur.execute("DELETE FROM custom_residues WHERE id=?", (rid,))
            self.conn.commit()

    def list_residues(self):
        with closing(self.conn.cursor()) as cur:
            cur.execute("SELECT * FROM custom_residues ORDER BY code")
            return [dict(r) for r in cur.fetchall()]

    # ---------------- modificações customizadas ----------------
    def add_modification(self, name, formula, targets, position, description=""):
        with closing(self.conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO custom_modifications "
                "(name, formula, targets, position, description) "
                "VALUES (?,?,?,?,?)",
                (name, formula, targets, position, description))
            self.conn.commit()
            return cur.lastrowid

    def delete_modification(self, mid):
        with closing(self.conn.cursor()) as cur:
            cur.execute("DELETE FROM custom_modifications WHERE id=?", (mid,))
            self.conn.commit()

    def list_modifications(self):
        with closing(self.conn.cursor()) as cur:
            cur.execute("SELECT * FROM custom_modifications ORDER BY name")
            return [dict(r) for r in cur.fetchall()]

    # ---------------- peptídeos salvos ----------------
    def save_peptide(self, name, sequence, n_term="", c_term="",
                     residue_mods="[]", notes=""):
        """Insere ou atualiza (por nome) um peptídeo salvo."""
        with closing(self.conn.cursor()) as cur:
            cur.execute("""
                INSERT INTO saved_peptides
                    (name, sequence, n_term_mod, c_term_mod, residue_mods, notes)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET
                    sequence=excluded.sequence, n_term_mod=excluded.n_term_mod,
                    c_term_mod=excluded.c_term_mod,
                    residue_mods=excluded.residue_mods, notes=excluded.notes
            """, (name, sequence, n_term, c_term, residue_mods, notes))
            self.conn.commit()

    def list_peptides(self):
        with closing(self.conn.cursor()) as cur:
            cur.execute("SELECT * FROM saved_peptides ORDER BY name")
            return [dict(r) for r in cur.fetchall()]

    def get_peptide(self, name):
        with closing(self.conn.cursor()) as cur:
            cur.execute("SELECT * FROM saved_peptides WHERE name=?", (name,))
            r = cur.fetchone()
            return dict(r) if r else None

    def rename_peptide(self, old, new):
        with closing(self.conn.cursor()) as cur:
            cur.execute("UPDATE saved_peptides SET name=? WHERE name=?",
                        (new, old))
            self.conn.commit()

    def delete_peptide(self, name):
        with closing(self.conn.cursor()) as cur:
            cur.execute("DELETE FROM saved_peptides WHERE name=?", (name,))
            self.conn.commit()

    # ---------------- metadados (flags internas) ----------------
    def get_meta(self, key):
        with closing(self.conn.cursor()) as cur:
            cur.execute("SELECT value FROM meta WHERE key=?", (key,))
            r = cur.fetchone()
            return r["value"] if r else None

    def set_meta(self, key, value):
        with closing(self.conn.cursor()) as cur:
            cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
                        (key, value))
            self.conn.commit()

    def close(self):
        self.conn.close()
