"""
Flask Application for Tumble Tower
Server-rendered web application conforming strictly to:
- Pure Python 3 & Flask
- Pure HTML5 and CSS3 (Zero JavaScript)
- SQLite database storage
- Custom Data Structures (Stack, Queue, LinkedList)
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from .game_engine import GameEngine
from .database import Database
from .game_rules import GameRules

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "tumble_tower_cs_secret_key_2026")

db = Database()

# In-memory active game engine instance cache
active_games = {}

def get_or_create_engine():
    """Retrieve active game engine from cache or SQLite database."""
    game_id = session.get("current_game_id")
    if game_id and game_id in active_games:
        return active_games[game_id]
    
    # Try loading from database
    if game_id:
        data = db.load_game(game_id)
        if data:
            engine = GameEngine.from_dict(data)
            active_games[game_id] = engine
            return engine

    # Check if any in-progress game exists in database
    saved = db.list_saved_games(limit=1)
    if saved:
        saved_id = saved[0]["id"]
        data = db.load_game(saved_id)
        if data:
            engine = GameEngine.from_dict(data)
            active_games[saved_id] = engine
            session["current_game_id"] = saved_id
            return engine

    # Otherwise create a brand new default game
    players = [p["name"] for p in db.get_all_players()[:3]]
    if not players:
        players = ["Player 1", "Player 2"]
    engine = GameEngine(difficulty="medium")
    engine.setup_new_game(players, difficulty="medium")
    active_games[engine.game_id] = engine
    session["current_game_id"] = engine.game_id
    db.save_game(engine.to_dict())
    return engine

def sync_game(engine):
    """Save game state to SQLite."""
    active_games[engine.game_id] = engine
    session["current_game_id"] = engine.game_id
    db.save_game(engine.to_dict())
    if engine.status in ("collapsed", "completed") and engine.winner:
        all_players = engine.player_queue.display()
        db.record_player_win(engine.winner, all_players)


# --- 1. Home Dashboard ---
@app.route("/")
@app.route("/dashboard")
def dashboard():
    engine = get_or_create_engine()
    game_dict = engine.to_dict()
    stats_summary = db.get_statistics_summary()
    saved_games = db.list_saved_games(limit=5)
    return render_template(
        "dashboard.html",
        game=game_dict,
        stats=stats_summary,
        saved_games=saved_games,
        active_page="dashboard"
    )


# --- 2. New Game Setup ---
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        selected_players = request.form.getlist("players")
        custom_player = request.form.get("custom_player", "").strip()
        difficulty = request.form.get("difficulty", "medium").lower()

        players_list = [p.strip() for p in selected_players if p.strip()]
        if custom_player:
            db.add_player(custom_player)
            if custom_player not in players_list:
                players_list.append(custom_player)

        if not players_list:
            flash("Please select or add at least 1 player to start a game.", "error")
            return redirect(url_for("setup"))

        # Create new engine
        engine = GameEngine(difficulty=difficulty)
        engine.setup_new_game(players_list, difficulty=difficulty)
        sync_game(engine)
        flash(f"New game started ({difficulty.capitalize()} mode) with {len(players_list)} players!", "success")
        return redirect(url_for("gameplay"))

    all_players = db.get_all_players()
    saved_games = db.list_saved_games(limit=5)
    return render_template(
        "setup.html",
        all_players=all_players,
        saved_games=saved_games,
        active_page="setup"
    )


# --- 3. Game Play ---
@app.route("/game")
def gameplay():
    engine = get_or_create_engine()
    game_dict = engine.to_dict()

    # Pre-calculate accessibility of all blocks for visual highlights
    accessible_block_ids = set()
    for lvl in game_dict["levels"]:
        for blk in lvl["blocks"]:
            if blk:
                block_obj = engine.tower.find_block(blk["id"])
                if block_obj:
                    is_acc, _ = GameRules.is_block_accessible(engine.tower, block_obj)
                    if is_acc:
                        accessible_block_ids.add(blk["id"])

    return render_template(
        "game.html",
        game=game_dict,
        accessible_ids=accessible_block_ids,
        active_page="game"
    )


# --- Game Actions (POST without JS) ---
@app.route("/game/select", methods=["POST"])
def game_select():
    engine = get_or_create_engine()
    block_id = request.form.get("block_id", "").strip()
    if not block_id:
        flash("No block was selected.", "error")
        return redirect(url_for("gameplay"))

    is_accessible, msg = engine.select_block(block_id)
    if is_accessible:
        flash(f"Block {block_id} selected. It is accessible for extraction!", "success")
    else:
        flash(f"Block {block_id} selected: {msg}", "error")

    sync_game(engine)
    return redirect(url_for("gameplay"))


@app.route("/game/remove", methods=["POST"])
def game_remove():
    engine = get_or_create_engine()
    success, msg = engine.remove_selected_block()
    if success:
        if engine.status == "collapsed":
            flash(msg, "error")
        else:
            flash(msg, "success")
    else:
        flash(msg, "error")

    sync_game(engine)
    return redirect(url_for("gameplay"))


@app.route("/game/place", methods=["POST"])
def game_place():
    engine = get_or_create_engine()
    success, msg = engine.place_held_block()
    if success:
        if engine.status == "collapsed":
            flash(msg, "error")
        else:
            flash(msg, "success")
    else:
        flash(msg, "error")

    sync_game(engine)
    return redirect(url_for("gameplay"))


@app.route("/game/undo", methods=["POST"])
def game_undo():
    engine = get_or_create_engine()
    success, msg = engine.undo_move()
    if success:
        flash(msg, "success")
    else:
        flash(msg, "error")

    sync_game(engine)
    return redirect(url_for("gameplay"))


@app.route("/game/restart", methods=["POST"])
def game_restart():
    engine = get_or_create_engine()
    players = engine.player_queue.display()
    difficulty = engine.difficulty
    engine.setup_new_game(players, difficulty=difficulty)
    sync_game(engine)
    flash("Tower rebuilt from foundation! Ready for turn 1.", "success")
    return redirect(url_for("gameplay"))


@app.route("/game/load/<game_id>")
def load_game(game_id):
    data = db.load_game(game_id)
    if data:
        engine = GameEngine.from_dict(data)
        active_games[game_id] = engine
        session["current_game_id"] = game_id
        flash(f"Loaded saved game #{game_id}.", "success")
    else:
        flash(f"Saved game #{game_id} could not be found.", "error")
    return redirect(url_for("gameplay"))


# --- 4. Player Management ---
@app.route("/players")
def players():
    all_players = db.get_all_players()
    return render_template("players.html", players=all_players, active_page="players")


@app.route("/players/add", methods=["POST"])
def add_player():
    name = request.form.get("name", "").strip()
    success, msg = db.add_player(name)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "error")
    return redirect(url_for("players"))


@app.route("/players/remove", methods=["POST"])
def remove_player():
    name = request.form.get("name", "").strip()
    deleted = db.remove_player(name)
    if deleted:
        flash(f"Player '{name}' removed from roster.", "success")
    else:
        flash(f"Player '{name}' could not be removed.", "error")
    return redirect(url_for("players"))


# --- 5. Block Search ---
@app.route("/search", methods=["GET", "POST"])
def search():
    engine = get_or_create_engine()
    query_type = request.values.get("query_type", "all")
    query_val = request.values.get("query_val", "").strip()

    results = []
    if query_val or request.method == "POST":
        results = engine.search_blocks(query_type=query_type, query_val=query_val)
    else:
        # Default: show all 54 blocks
        results = engine.search_blocks(query_type="all", query_val="")

    return render_template(
        "search.html",
        results=results,
        query_type=query_type,
        query_val=query_val,
        total_found=len(results),
        active_page="search"
    )


# --- 6. Game History ---
@app.route("/history")
def history():
    engine = get_or_create_engine()
    game_dict = engine.to_dict()
    all_saved = db.list_all_games(limit=25)
    return render_template(
        "history.html",
        game=game_dict,
        all_games=all_saved,
        active_page="history"
    )


# --- 7. Tower Statistics ---
@app.route("/statistics")
def statistics():
    engine = get_or_create_engine()
    game_dict = engine.to_dict()
    stats_summary = db.get_statistics_summary()
    return render_template(
        "statistics.html",
        game=game_dict,
        stats=stats_summary,
        active_page="statistics"
    )


# --- 8. How to Play & DS Architecture ---
@app.route("/instructions")
@app.route("/rules")
def instructions():
    return render_template("instructions.html", active_page="instructions")


if __name__ == "__main__":
    # Ensure database is prepared
    db.init_db()
    # Run on port 3000 to bind to the AI Studio applet container
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
