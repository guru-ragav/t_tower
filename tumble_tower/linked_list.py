"""
Linked List Data Structure Implementation
Represents the tower levels sequentially as a Doubly Linked List.
Each LevelNode stores one floor/layer of the tower, its orientation (horizontal/vertical),
and its child blocks (at slot 0, 1, 2).
"""

from .block import Block

class LevelNode:
    """
    Node representing a single level/layer in the Tumble Tower.
    """
    def __init__(self, level_number, orientation="horizontal"):
        self.level_number = int(level_number)
        self.orientation = orientation  # "horizontal" (odd levels) or "vertical" (even levels)
        # 3 positions: 0 (Left), 1 (Center), 2 (Right). None if vacant slot.
        self.blocks = [None, None, None]
        self.next = None  # Points to level above (higher level number)
        self.prev = None  # Points to level below (lower level number)

    @property
    def block_count(self):
        """Count of active blocks currently present in this level."""
        return sum(1 for b in self.blocks if b is not None)

    @property
    def is_complete(self):
        """A level is complete if all 3 slots are occupied."""
        return self.block_count == 3

    @property
    def is_empty(self):
        """A level is empty if no blocks remain."""
        return self.block_count == 0

    def get_block(self, position):
        """Get block at slot 0, 1, or 2."""
        if 0 <= position <= 2:
            return self.blocks[position]
        return None

    def set_block(self, position, block):
        """Place block into specific slot 0, 1, or 2."""
        if 0 <= position <= 2:
            self.blocks[position] = block
            if block:
                block.level = self.level_number
                block.position = position
            return True
        return False

    def remove_block(self, position):
        """Remove and return block from slot."""
        if 0 <= position <= 2:
            block = self.blocks[position]
            self.blocks[position] = None
            return block
        return None

    def to_dict(self):
        """Serialize level node to dictionary for templates and storage."""
        return {
            "level_number": self.level_number,
            "orientation": self.orientation,
            "block_count": self.block_count,
            "is_complete": self.is_complete,
            "is_empty": self.is_empty,
            "blocks": [b.to_dict() if b else None for b in self.blocks]
        }


class LinkedList:
    """
    Doubly Linked List managing the tower levels from base (level 1) to apex.
    """
    def __init__(self):
        self.head = None  # Level 1 (ground foundation)
        self.tail = None  # Highest level
        self._level_map = {}  # Fast level number lookup

    def insert_level(self, level_number=None, orientation=None):
        """
        Append a new level to the top of the tower.
        If level_number is None, defaults to current top + 1.
        Orientation defaults to alternating ('horizontal' for odd, 'vertical' for even).
        """
        if level_number is None:
            level_number = (self.tail.level_number + 1) if self.tail else 1

        if orientation is None:
            orientation = "horizontal" if (level_number % 2 != 0) else "vertical"

        new_node = LevelNode(level_number, orientation)

        if not self.head:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node

        self._level_map[level_number] = new_node
        return new_node

    def find_level(self, level_number):
        """Return the LevelNode for a given level number, or None."""
        return self._level_map.get(int(level_number))

    def insert_block(self, level_number, block, position=None):
        """
        Insert a block into a level.
        If position is None, chooses the first vacant slot (0, 1, or 2).
        """
        node = self.find_level(level_number)
        if not node:
            node = self.insert_level(level_number)

        if position is None:
            # Find first empty slot
            for idx in range(3):
                if node.blocks[idx] is None:
                    position = idx
                    break

        if position is not None and 0 <= position <= 2:
            node.set_block(position, block)
            return True
        return False

    def delete_block(self, block_id):
        """
        Locate and delete a block across the linked list by its unique ID.
        Returns the removed Block object, or None if not found.
        """
        curr = self.head
        while curr:
            for idx, blk in enumerate(curr.blocks):
                if blk and blk.id == str(block_id):
                    removed = curr.remove_block(idx)
                    return removed
            curr = curr.next
        return None

    def find_block(self, block_id):
        """Locate a block by ID without deleting it."""
        curr = self.head
        while curr:
            for blk in curr.blocks:
                if blk and blk.id == str(block_id):
                    return blk
            curr = curr.next
        return None

    def get_top_level(self):
        """Return the highest LevelNode."""
        return self.tail

    def get_level_count(self):
        """Return total number of levels."""
        return len(self._level_map)

    def count_blocks(self):
        """Count total active blocks currently in the tower."""
        total = 0
        curr = self.head
        while curr:
            total += curr.block_count
            curr = curr.next
        return total

    def traverse(self, from_top=True):
        """
        Traverse all level nodes.
        from_top=True: Top down (from highest level to level 1), ideal for UI tower rendering.
        from_top=False: Bottom up (from level 1 to top).
        """
        nodes = []
        if from_top:
            curr = self.tail
            while curr:
                nodes.append(curr)
                curr = curr.prev
        else:
            curr = self.head
            while curr:
                nodes.append(curr)
                curr = curr.next
        return nodes

    def display(self):
        """String representation of the linked list for terminal / inspection."""
        lines = []
        curr = self.tail
        while curr:
            slots = [b.id if b else "---" for b in curr.blocks]
            lines.append(f"Level {curr.level_number:02d} [{curr.orientation[:1].upper()}]: {' | '.join(slots)}")
            curr = curr.prev
        return "\n".join(lines)

    def to_list(self):
        """Serialize full linked list into serializable dict/list structure."""
        serialized = []
        curr = self.head
        while curr:
            serialized.append(curr.to_dict())
            curr = curr.next
        return serialized

    @classmethod
    def from_list(cls, data_list):
        """Reconstruct linked list from serialized dictionary list."""
        ll = cls()
        for lvl_data in data_list:
            node = ll.insert_level(
                level_number=lvl_data["level_number"],
                orientation=lvl_data.get("orientation", "horizontal")
            )
            for idx, blk_data in enumerate(lvl_data.get("blocks", [])):
                if blk_data:
                    blk = Block.from_dict(blk_data)
                    node.set_block(idx, blk)
        return ll
