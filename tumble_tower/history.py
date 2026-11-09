"""
Game History and Undo Management
Uses Stack data structure to track all game operations chronologically.
Provides multi-step undo capabilities to restore tower arrangement,
block positions, player turn queues, and statistics.
"""

from datetime import datetime
from .stack import Stack

class MoveRecord:
    """
    Data record representing a single complete valid turn operation.
    """
    def __init__(self, move_number, player_name, block_id, prev_level, prev_position,
                 new_level, new_position, operation="remove_and_place", timestamp=None,
                 snapshot=None):
        self.move_number = int(move_number)
        self.player_name = str(player_name)
        self.block_id = str(block_id)
        self.prev_level = int(prev_level)
        self.prev_position = int(prev_position)
        self.new_level = int(new_level)
        self.new_position = int(new_position)
        self.operation = str(operation)
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Full serializable snapshot of the tower and players before this move
        self.snapshot = snapshot or {}

    def to_dict(self):
        """Serialize record to dictionary."""
        return {
            "move_number": self.move_number,
            "player_name": self.player_name,
            "block_id": self.block_id,
            "prev_level": self.prev_level,
            "prev_position": self.prev_position,
            "new_level": self.new_level,
            "new_position": self.new_position,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "snapshot": self.snapshot
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            move_number=data.get("move_number", 0),
            player_name=data.get("player_name", "Unknown"),
            block_id=data.get("block_id", ""),
            prev_level=data.get("prev_level", 0),
            prev_position=data.get("prev_position", 0),
            new_level=data.get("new_level", 0),
            new_position=data.get("new_position", 0),
            operation=data.get("operation", "remove_and_place"),
            timestamp=data.get("timestamp"),
            snapshot=data.get("snapshot", {})
        )

    def summary(self):
        pos_names = {0: "Left", 1: "Center", 2: "Right"}
        prev_p = pos_names.get(self.prev_position, str(self.prev_position))
        new_p = pos_names.get(self.new_position, str(self.new_position))
        return (
            f"Move #{self.move_number}: {self.player_name} moved {self.block_id} "
            f"from L{self.prev_level} ({prev_p}) to L{self.new_level} ({new_p})"
        )


class HistoryStack:
    """
    History tracker powered by a custom LIFO Stack.
    """
    def __init__(self):
        self._stack = Stack(name="GameHistoryStack")

    def record_move(self, move_record):
        """Push a new move record onto the history stack."""
        self._stack.push(move_record)

    def undo_last_move(self):
        """
        Pop and return the most recent move record.
        Returns None if no moves exist to undo.
        """
        return self._stack.pop()

    def peek_last_move(self):
        """View the latest move record without popping."""
        return self._stack.peek()

    def is_empty(self):
        """Check if history is empty."""
        return self._stack.is_empty()

    def count(self):
        """Total recorded moves."""
        return self._stack.size()

    def get_all_moves(self, chronological=True):
        """
        Return all move records.
        chronological=True: Earliest move first (Move #1, #2, ...).
        chronological=False: Most recent move first.
        """
        items = self._stack.to_list()
        if not chronological:
            return list(reversed(items))
        return items

    def clear(self):
        self._stack.clear()

    def to_list(self):
        return [m.to_dict() for m in self._stack.to_list()]

    @classmethod
    def from_list(cls, data_list):
        history = cls()
        for item in data_list:
            history.record_move(MoveRecord.from_dict(item))
        return history
