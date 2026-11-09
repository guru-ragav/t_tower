"""
SQLite Database Layer
Stores:
- Players (names, games played, games won)
- Games (active, saved, completed games, difficulty, current state)
- Blocks (persistent block locations for games)
- Game History (full move logs)
- Statistics (aggregate performance records)
"""

import sqlite3
import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "tumble_tower.db")

class Database:
    """
    SQLite persistence manager for Tumble Tower.
    """
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Create a connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize all required tables if they don't already exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Players Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    games_played INTEGER DEFAULT 0,
                    games_won INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            # Games Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,       -- 'in_progress', 'collapsed', 'completed'
                    difficulty TEXT NOT NULL,   -- 'easy', 'medium', 'hard'
                    current_player TEXT,
                    winner TEXT,
                    total_moves INTEGER DEFAULT 0,
                    total_levels INTEGER DEFAULT 18,
                    blocks_remaining INTEGER DEFAULT 54,
                    collapse_reason TEXT,
                    game_data TEXT NOT NULL,    -- Complete JSON serialization of engine state
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Blocks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    number INTEGER NOT NULL,
                    color TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (id, game_id),
                    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
                )
            """)

            # Game History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    move_number INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    block_id TEXT NOT NULL,
                    prev_level INTEGER NOT NULL,
                    prev_position INTEGER NOT NULL,
                    new_level INTEGER NOT NULL,
                    new_position INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
                )
            """)

            # Statistics Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    moves_count INTEGER DEFAULT 0,
                    highest_level INTEGER DEFAULT 18,
                    wobbly_count INTEGER DEFAULT 0,
                    collapse_level INTEGER,
                    winner TEXT,
                    completed_at TEXT NOT NULL
                )
            """)

            conn.commit()

            # Seed default players if empty
            cursor.execute("SELECT COUNT(*) FROM players")
            if cursor.fetchone()[0] == 0:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.executemany(
                    "INSERT INTO players (name, games_played, games_won, created_at) VALUES (?, ?, ?, ?)",
                    [
                        ("Alex", 3, 2, now),
                        ("Sam", 3, 1, now),
                        ("Taylor", 2, 0, now)
                    ]
                )
                conn.commit()

    # --- Player Operations ---
    def add_player(self, name):
        """Add a new player. Returns True if added, False if duplicate."""
        cleaned = name.strip()
        if not cleaned:
            return False, "Player name cannot be empty."
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO players (name, created_at) VALUES (?, ?)",
                    (cleaned, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                return True, f"Player '{cleaned}' added successfully."
        except sqlite3.IntegrityError:
            return False, f"Player '{cleaned}' already exists."

    def remove_player(self, name):
        """Remove a player by name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM players WHERE name = ?", (name.strip(),))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_all_players(self):
        """Get list of all players ordered by games won."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players ORDER BY games_won DESC, games_played DESC, name ASC")
            return [dict(row) for row in cursor.fetchall()]

    def record_player_win(self, winner_name, all_players):
        """Update games played for all participants and increment win for winner."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for p in all_players:
                cursor.execute(
                    "UPDATE players SET games_played = games_played + 1 WHERE name = ?",
                    (p,)
                )
            if winner_name:
                cursor.execute(
                    "UPDATE players SET games_won = games_won + 1 WHERE name = ?",
                    (winner_name,)
                )
            conn.commit()

    # --- Game Operations ---
    def save_game(self, game_state):
        """
        Saves or updates a game and its blocks and history in the database.
        game_state: dictionary containing complete serialized game engine state.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        game_id = game_state["game_id"]
        status = game_state.get("status", "in_progress")
        difficulty = game_state.get("difficulty", "medium")
        current_player = game_state.get("current_player", "")
        winner = game_state.get("winner", None)
        total_moves = game_state.get("total_moves", 0)
        total_levels = game_state.get("total_levels", 18)
        blocks_remaining = game_state.get("blocks_remaining", 54)
        collapse_reason = game_state.get("collapse_reason", "")
        game_data_json = json.dumps(game_state)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Upsert game record
            cursor.execute("""
                INSERT INTO games (
                    id, status, difficulty, current_player, winner, total_moves,
                    total_levels, blocks_remaining, collapse_reason, game_data, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    difficulty=excluded.difficulty,
                    current_player=excluded.current_player,
                    winner=excluded.winner,
                    total_moves=excluded.total_moves,
                    total_levels=excluded.total_levels,
                    blocks_remaining=excluded.blocks_remaining,
                    collapse_reason=excluded.collapse_reason,
                    game_data=excluded.game_data,
                    updated_at=excluded.updated_at
            """, (
                game_id, status, difficulty, current_player, winner, total_moves,
                total_levels, blocks_remaining, collapse_reason, game_data_json, now, now
            ))

            # Upsert blocks table
            cursor.execute("DELETE FROM blocks WHERE game_id = ?", (game_id,))
            blocks_to_insert = []
            for b in game_state.get("all_blocks", []):
                blocks_to_insert.append((
                    b["id"], game_id, b["number"], b["color"],
                    b["level"], b["position"], b["status"]
                ))
            if blocks_to_insert:
                cursor.executemany("""
                    INSERT INTO blocks (id, game_id, number, color, level, position, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, blocks_to_insert)

            # Upsert game history records
            cursor.execute("DELETE FROM game_history WHERE game_id = ?", (game_id,))
            history_rows = []
            for m in game_state.get("history", []):
                history_rows.append((
                    game_id, m["move_number"], m["player_name"], m["block_id"],
                    m["prev_level"], m["prev_position"], m["new_level"], m["new_position"],
                    m["operation"], m["timestamp"]
                ))
            if history_rows:
                cursor.executemany("""
                    INSERT INTO game_history (
                        game_id, move_number, player_name, block_id, prev_level,
                        prev_position, new_level, new_position, operation, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, history_rows)

            # If game is completed or collapsed, record in statistics table if not recorded yet
            if status in ("completed", "collapsed"):
                cursor.execute("SELECT id FROM statistics WHERE game_id = ?", (game_id,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO statistics (
                            game_id, moves_count, highest_level, wobbly_count,
                            collapse_level, winner, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        game_id, total_moves, total_levels,
                        game_state.get("wobbly_count", 0),
                        game_state.get("collapse_level", None),
                        winner, now
                    ))

            conn.commit()

    def load_game(self, game_id):
        """Retrieve full game state by game_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT game_data FROM games WHERE id = ?", (game_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["game_data"])
        return None

    def list_saved_games(self, limit=10):
        """List active/in-progress games available to resume."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status, difficulty, current_player, total_moves, total_levels, updated_at
                FROM games
                WHERE status = 'in_progress'
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def list_all_games(self, limit=20):
        """List recent games regardless of status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status, difficulty, current_player, winner, total_moves, total_levels, updated_at, collapse_reason
                FROM games
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics_summary(self):
        """Get aggregate statistics across all played games."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total games count
            cursor.execute("SELECT COUNT(*) FROM games")
            total_games = cursor.fetchone()[0]

            # Completed vs In-progress
            cursor.execute("SELECT COUNT(*) FROM games WHERE status IN ('completed', 'collapsed')")
            finished_games = cursor.fetchone()[0]

            # Max level achieved
            cursor.execute("SELECT MAX(total_levels) FROM games")
            max_level = cursor.fetchone()[0] or 18

            # Average moves per game
            cursor.execute("SELECT AVG(total_moves) FROM games WHERE status != 'in_progress'")
            avg_moves = cursor.fetchone()[0] or 0.0

            # Leaderboard
            cursor.execute("SELECT name, games_played, games_won FROM players WHERE games_played > 0 ORDER BY games_won DESC, games_played DESC LIMIT 5")
            leaderboard = [dict(row) for row in cursor.fetchall()]

            # Recent finished games
            cursor.execute("""
                SELECT g.id, g.status, g.difficulty, g.winner, g.total_moves, g.total_levels, g.updated_at, g.collapse_reason
                FROM games g
                WHERE g.status IN ('completed', 'collapsed')
                ORDER BY g.updated_at DESC LIMIT 5
            """)
            recent_games = [dict(row) for row in cursor.fetchall()]

            return {
                "total_games": total_games,
                "finished_games": finished_games,
                "max_level": max_level,
                "avg_moves": round(float(avg_moves), 1),
                "leaderboard": leaderboard,
                "recent_games": recent_games
            }
