"""
Stack Data Structure Implementation
Provides LIFO (Last-In-First-Out) operations for:
- Tower block management
- Temporary auxiliary storage during block extraction
- Game history tracking
- Multi-step Undo operations
"""

class Stack:
    """
    Native Python Stack implementation using linked or list-backed nodes.
    Follows strict LIFO principle.
    """
    def __init__(self, name="Stack"):
        self.name = name
        self._items = []

    def push(self, item):
        """Push an item onto the top of the stack."""
        self._items.append(item)

    def pop(self):
        """
        Remove and return the top item from the stack.
        Returns None if stack is empty.
        """
        if self.is_empty():
            return None
        return self._items.pop()

    def peek(self):
        """
        Return the top item without removing it.
        Returns None if stack is empty.
        """
        if self.is_empty():
            return None
        return self._items[-1]

    def is_empty(self):
        """Check if the stack contains no items."""
        return len(self._items) == 0

    def size(self):
        """Return the number of items currently in the stack."""
        return len(self._items)

    def display(self):
        """
        Return a copy of the stack items from top to bottom.
        Useful for visualization and debugging.
        """
        return list(reversed(self._items))

    def clear(self):
        """Empty the stack."""
        self._items.clear()

    def to_list(self):
        """Return raw list representation from bottom to top."""
        return list(self._items)

    @classmethod
    def from_list(cls, items, name="Stack"):
        """Create a stack populated from a list (index 0 is bottom)."""
        stack = cls(name=name)
        stack._items = list(items)
        return stack

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        # Iterate from top to bottom (LIFO)
        return iter(reversed(self._items))

    def __repr__(self):
        return f"Stack({self.name}, size={len(self._items)}, top={self.peek()})"
