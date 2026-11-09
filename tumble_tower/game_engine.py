"""
Tumble Tower Game Engine
Integrates:
- Stack: Auxiliary block manipulation and multi-level Undo history
- Queue: FIFO player turn rotation
- LinkedList: Doubly linked hierarchy of tower levels
- Block & GameRules: Physical constraints, accessibility, and deterministic stability
- Database: Persistence and session recovery
"""

import uuid
from datetime import datetime
from .block import Block, WOOD_PALETTES
from .stack import Stack
from .queue import Queue
from .linked_list import LinkedList
from .game_rules import GameRules
from .history import HistoryStack, MoveRecord

class GameEngine:
    """
    Stateful controller managing an active Tumble Tower match.
    """
    def __init__(self, game_id=None, difficulty="medium"):
        self.game_id = game_id or f"TT-{uuid.uuid4().hex[:8].upper()}"
        self.difficulty = difficulty.lower()  # easy, medium, hard
        self.status = "in_progress"           # in_progress, collapsed, completed
        self.tower = LinkedList()
        self.player_queue = Queue(name="PlayerTurnQueue")
        self.history_stack = HistoryStack()
        self.auxiliary_stack = Stack(name="AuxiliaryBlockStack")
        
        # Turn and interaction state
        self.selected_block_id = None
        self.held_block = None               # Block currently extracted and waiting to be placed
        self.last_move_record = None
        self.auxiliary_trace = []            # Trace of CS stack operations during extraction
        self.winner = None
        self.collapse_reason = None
        self.collapse_level = None
        self.total_moves = 0
        self.wobbly_moves_count = 0
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Tower Initialization ---
    def setup_new_game(self, player_names, difficulty="medium"):
        """
        Creates an 18-level tower with 3 blocks per level (54 blocks total).
        Populates the player queue in given order.
        """
        self.difficulty = difficulty.lower()
        self.tower = LinkedList()
        self.player_queue.clear()
        self.history_stack.clear()
        self.auxiliary_stack.clear()
        self.selected_block_id = None
        self.held_block = None
        self.winner = None
        self.collapse_reason = None
        self.collapse_level = None
        self.total_moves = 0
        self.wobbly_moves_count = 0
        self.status = "in_progress"
        self.auxiliary_trace = []

        # Populate Player Queue (FIFO)
        cleaned_players = [p.strip() for p in player_names if p.strip()]
        if not cleaned_players:
            cleaned_players = ["Player 1", "Player 2"]
        for p in cleaned_players:
            self.player_queue.enqueue(p)

        # Build 18 levels, alternating orientations
        block_counter = 1
        palette_len = len(WOOD_PALETTES)

        for lvl in range(1, 19):
            orientation = "horizontal" if (lvl % 2 != 0) else "vertical"
            level_node = self.tower.insert_level(level_number=lvl, orientation=orientation)
            for pos in range(3):
                palette = WOOD_PALETTES[(block_counter - 1) % palette_len]
                block_id = f"BLK-{block_counter:02d}"
                block = Block(
                    block_id=block_id,
                    number=block_counter,
                    color=palette["name"],
                    level=lvl,
                    position=pos,
                    status="in_tower",
                    hex_color=palette["hex"],
                    dark_hex=palette["dark"]
                )
                level_node.set_block(pos, block)
                block_counter += 1

        return self

    # --- Block Selection ---
    def select_block(self, block_id):
        """
        Select a block in the tower for inspection and potential extraction.
        """
        if self.status != "in_progress":
            return False, "Game is already finished."

        if self.held_block:
            return False, f"You are currently holding block {self.held_block.id}. Place it on top before selecting another."

        block = self.tower.find_block(block_id)
        if not block:
            return False, f"Block {block_id} not found in the tower."

        self.selected_block_id = block.id
        is_accessible, reason = GameRules.is_block_accessible(self.tower, block)
        return is_accessible, reason

    # --- Block Extraction with Auxiliary Stack Demonstration ---
    def remove_selected_block(self):
        """
        Extracts the selected block from the tower according to assignment rules:
        - Temporarily stores blocks above the selected block using an auxiliary stack.
        - Removes the target block.
        - Restores upper blocks in their original order (LIFO reverse of push).
        - Computes stability and potential collapse.
        """
        if self.status != "in_progress":
            return False, "Game is already finished."

        if self.held_block:
            return False, f"Already holding block {self.held_block.id}. Place it on top first."

        if not self.selected_block_id:
            return False, "No block selected to remove."

        target_block = self.tower.find_block(self.selected_block_id)
        if not target_block:
            return False, "Selected block no longer exists in tower."

        is_accessible, rule_msg = GameRules.is_block_accessible(self.tower, target_block)
        if not is_accessible:
            return False, rule_msg

        target_level = target_block.level
        # Capture snapshot BEFORE extraction so undo fully restores the tower layout
        self.pre_extraction_snapshot = self.create_snapshot()
        self.auxiliary_trace = []
        self.auxiliary_stack.clear()

        # CS Data Structure Demonstration:
        # Traverse levels above target_level, push their blocks to auxiliary_stack
        all_levels_ascending = self.tower.traverse(from_top=False)
        upper_levels = [lvl for lvl in all_levels_ascending if lvl.level_number > target_level]

        self.auxiliary_trace.append({
            "step": 1,
            "action": "INIT_AUXILIARY_STACK",
            "description": f"Preparing auxiliary stack to temporarily hold upper blocks above Level {target_level}."
        })

        # Pop blocks from levels above and push to auxiliary stack
        pushed_count = 0
        for lvl in upper_levels:
            for pos in range(3):
                blk = lvl.blocks[pos]
                if blk:
                    # Store tuple (level_number, position, block)
                    self.auxiliary_stack.push((lvl.level_number, pos, blk))
                    self.auxiliary_trace.append({
                        "step": len(self.auxiliary_trace) + 1,
                        "action": "PUSH_TO_AUXILIARY_STACK",
                        "block_id": blk.id,
                        "description": f"Pushed {blk.id} (L{lvl.level_number}, Pos {pos}) to auxiliary stack."
                    })
                    pushed_count += 1

        # Extract target block from target level
        target_lvl_node = self.tower.find_level(target_level)
        removed_block = target_lvl_node.remove_block(target_block.position)
        removed_block.status = "removed"
        self.held_block = removed_block

        self.auxiliary_trace.append({
            "step": len(self.auxiliary_trace) + 1,
            "action": "EXTRACT_TARGET_BLOCK",
            "block_id": removed_block.id,
            "description": f"Extracted target block {removed_block.id} from Level {target_level}, Position {removed_block.position}."
        })

        # Restore upper blocks from auxiliary stack in reverse order
        restored_count = 0
        while not self.auxiliary_stack.is_empty():
            lvl_num, pos, blk = self.auxiliary_stack.pop()
            lvl_node = self.tower.find_level(lvl_num)
            lvl_node.set_block(pos, blk)
            self.auxiliary_trace.append({
                "step": len(self.auxiliary_trace) + 1,
                "action": "POP_AND_RESTORE",
                "block_id": blk.id,
                "description": f"Popped {blk.id} from auxiliary stack and restored to Level {lvl_num}, Position {pos}."
            })
            restored_count += 1

        self.auxiliary_trace.append({
            "step": len(self.auxiliary_trace) + 1,
            "action": "COMPLETE",
            "description": f"Successfully extracted {removed_block.id}. {restored_count} upper blocks restored in original order."
        })

        # Check immediate stability after removal
        stability = GameRules.calculate_stability(self.tower, self.difficulty)
        if stability["status"] == "collapsed":
            self.status = "collapsed"
            self.collapse_reason = stability["reason"]
            self.collapse_level = stability["collapsed_level"]
            current_player = self.player_queue.peek()
            # Winner is previous player!
            players_list = self.player_queue.display()
            self.winner = players_list[-1] if len(players_list) > 1 else current_player
            return True, f"TOWER COLLAPSED during removal! {stability['reason']}"

        self.selected_block_id = None
        return True, f"Block {removed_block.id} successfully extracted! Now place it on top of the tower."

    # --- Block Placement at Apex ---
    def place_held_block(self):
        """
        Places the currently held block onto the topmost level:
        - Fills current top level (Left, Center, Right).
        - If top level has 3 blocks, creates a new level with alternating orientation.
        - Creates a history snapshot and records move in HistoryStack for undo.
        - Evaluates stability: triggers collapse or passes turn to next player in queue.
        """
        if self.status != "in_progress":
            return False, "Game is already finished."

        if not self.held_block:
            return False, "You are not holding any extracted block to place."

        block = self.held_block
        current_player = self.player_queue.peek()
        prev_level = block.level
        prev_position = block.position

        # Capture snapshot of the state BEFORE this complete move for Undo
        snapshot = getattr(self, "pre_extraction_snapshot", None) or self.create_snapshot()
        self.pre_extraction_snapshot = None

        # Find or create top placement slot
        top_node = self.tower.get_top_level()
        placed_level = top_node.level_number
        placed_position = None

        if top_node.is_complete:
            # Create a brand new level
            placed_level = top_node.level_number + 1
            new_orientation = "horizontal" if (placed_level % 2 != 0) else "vertical"
            new_top = self.tower.insert_level(level_number=placed_level, orientation=new_orientation)
            placed_position = 0
            new_top.set_block(placed_position, block)
        else:
            # Find first vacant slot in top level (0, 1, or 2)
            for pos in range(3):
                if top_node.blocks[pos] is None:
                    placed_position = pos
                    top_node.set_block(placed_position, block)
                    break

        block.status = "in_tower"
        self.held_block = None
        self.selected_block_id = None
        self.total_moves += 1

        # Record Move in History Stack (LIFO)
        move_rec = MoveRecord(
            move_number=self.total_moves,
            player_name=current_player,
            block_id=block.id,
            prev_level=prev_level,
            prev_position=prev_position,
            new_level=placed_level,
            new_position=placed_position,
            operation="remove_and_place",
            snapshot=snapshot
        )
        self.history_stack.record_move(move_rec)
        self.last_move_record = move_rec

        # Re-evaluate stability
        stability = GameRules.calculate_stability(self.tower, self.difficulty)
        if stability["status"] == "wobbly":
            self.wobbly_moves_count += 1

        if stability["status"] == "collapsed":
            self.status = "collapsed"
            self.collapse_reason = stability["reason"]
            self.collapse_level = stability["collapsed_level"]
            # Current player caused the tower to collapse!
            # Winner is the previous player in round-robin order:
            all_p = self.player_queue.display()
            self.winner = all_p[-1] if len(all_p) > 1 else current_player
            return True, f"TOWER COLLAPSED! {stability['reason']} Winner: {self.winner}!"

        # Advance turn via Queue FIFO rotation
        next_player = self.player_queue.rotate()

        return True, (
            f"Move #{self.total_moves} complete! {block.id} placed on Level {placed_level}. "
            f"Turn rotated: Next player is {next_player}."
        )

    # --- Multi-Step Undo Operation ---
    def undo_move(self):
        """
        Reverses the most recent valid move using HistoryStack:
        - Restores original tower layout and block coordinates
        - Restores player queue turn (rotates backward)
        - Updates level count and stability
        """
        # If currently holding a block, allow cancelling the extraction
        if self.held_block and getattr(self, "pre_extraction_snapshot", None):
            self.restore_from_snapshot(self.pre_extraction_snapshot)
            self.pre_extraction_snapshot = None
            self.held_block = None
            self.selected_block_id = None
            current_player = self.player_queue.peek()
            return True, f"Cancelled block extraction. Block returned to tower. Current turn: {current_player}."

        if self.status == "collapsed":
            # Allow undoing the fatal move to rescue the tower!
            pass
        elif self.status != "in_progress":
            return False, "Cannot undo in current game state."

        if self.history_stack.is_empty():
            return False, "No previous moves available in history to undo."

        last_move = self.history_stack.undo_last_move()
        if not last_move or not last_move.snapshot:
            return False, "Unable to restore previous snapshot."

        # Restore from snapshot
        self.restore_from_snapshot(last_move.snapshot)
        self.held_block = None
        self.selected_block_id = None
        self.status = "in_progress"
        self.winner = None
        self.collapse_reason = None
        self.collapse_level = None

        current_player = self.player_queue.peek()
        return True, (
            f"Undo successful! Reversed Move #{last_move.move_number} "
            f"({last_move.block_id} by {last_move.player_name}). Turn restored to {current_player}."
        )

    # --- Search Engine Implementation ---
    def search_blocks(self, query_type="all", query_val=""):
        """
        Search through all 54 blocks in the game by:
        - Block ID (e.g. 'BLK-07')
        - Block Number (e.g. 7)
        - Color / Wood tone (e.g. 'Walnut')
        - Level (e.g. 4)
        Returns detailed status, position, and accessibility for each matched block.
        """
        results = []
        all_levels = self.tower.traverse(from_top=False)
        
        # Traverse every block currently in tower
        for lvl in all_levels:
            for pos in range(3):
                blk = lvl.blocks[pos]
                if blk and blk.matches_query(query_type, query_val):
                    is_accessible, reason = GameRules.is_block_accessible(self.tower, blk)
                    results.append({
                        "block": blk.to_dict(),
                        "level": lvl.level_number,
                        "orientation": lvl.orientation,
                        "position_name": blk.position_name,
                        "is_accessible": is_accessible,
                        "status_reason": reason
                    })

        # Also search held block if any
        if self.held_block and self.held_block.matches_query(query_type, query_val):
            results.append({
                "block": self.held_block.to_dict(),
                "level": self.held_block.level,
                "orientation": "held",
                "position_name": "Held in Hand",
                "is_accessible": False,
                "status_reason": "Currently extracted and awaiting placement at top."
            })

        return results

    # --- Snapshot Serialization and Restoration ---
    def create_snapshot(self):
        """Creates a complete serializable representation of engine state."""
        return {
            "game_id": self.game_id,
            "difficulty": self.difficulty,
            "status": self.status,
            "total_moves": self.total_moves,
            "wobbly_moves_count": self.wobbly_moves_count,
            "player_queue": self.player_queue.to_list(),
            "tower": self.tower.to_list(),
            "selected_block_id": self.selected_block_id,
            "held_block": self.held_block.to_dict() if self.held_block else None,
            "winner": self.winner,
            "collapse_reason": self.collapse_reason,
            "collapse_level": self.collapse_level
        }

    def restore_from_snapshot(self, snapshot):
        """Restores complete engine state from a snapshot dictionary."""
        self.game_id = snapshot.get("game_id", self.game_id)
        self.difficulty = snapshot.get("difficulty", "medium")
        self.status = snapshot.get("status", "in_progress")
        self.total_moves = snapshot.get("total_moves", 0)
        self.wobbly_moves_count = snapshot.get("wobbly_moves_count", 0)
        self.winner = snapshot.get("winner")
        self.collapse_reason = snapshot.get("collapse_reason")
        self.collapse_level = snapshot.get("collapse_level")

        # Restore Player Queue
        self.player_queue = Queue.from_list(snapshot.get("player_queue", []))

        # Restore Linked List Tower
        self.tower = LinkedList.from_list(snapshot.get("tower", []))

        # Restore Selected and Held block
        self.selected_block_id = snapshot.get("selected_block_id")
        held_data = snapshot.get("held_block")
        self.held_block = Block.from_dict(held_data) if held_data else None

    # --- Full Export for Database and Templates ---
    def to_dict(self):
        """Export full game data for persistence and Jinja2 rendering."""
        stability = GameRules.calculate_stability(self.tower, self.difficulty)
        top_node = self.tower.get_top_level()
        all_levels = self.tower.traverse(from_top=True) # Top down for visual tower display

        all_blocks = []
        for lvl in all_levels:
            for b in lvl.blocks:
                if b:
                    all_blocks.append(b.to_dict())
        if self.held_block:
            all_blocks.append(self.held_block.to_dict())

        return {
            "game_id": self.game_id,
            "difficulty": self.difficulty,
            "status": self.status,
            "total_moves": self.total_moves,
            "total_levels": self.tower.get_level_count(),
            "blocks_remaining": self.tower.count_blocks(),
            "wobbly_moves_count": self.wobbly_moves_count,
            "current_player": self.player_queue.peek(),
            "next_player": self.player_queue.peek_next(),
            "player_queue": self.player_queue.display(),
            "players_list": self.player_queue.display(),
            "selected_block_id": self.selected_block_id,
            "held_block": self.held_block.to_dict() if self.held_block else None,
            "stability": stability,
            "levels": [lvl.to_dict() for lvl in all_levels],
            "all_blocks": all_blocks,
            "history": self.history_stack.to_list(),
            "auxiliary_trace": self.auxiliary_trace,
            "winner": self.winner,
            "collapse_reason": self.collapse_reason,
            "collapse_level": self.collapse_level,
            "created_at": self.created_at,
            "can_undo": not self.history_stack.is_empty()
        }

    @classmethod
    def from_dict(cls, data):
        """Instantiate an engine restored from database data."""
        engine = cls(game_id=data.get("game_id"), difficulty=data.get("difficulty", "medium"))
        engine.restore_from_snapshot(data)
        # Restore history stack if present
        if "history" in data:
            engine.history_stack = HistoryStack.from_list(data["history"])
        return engine
