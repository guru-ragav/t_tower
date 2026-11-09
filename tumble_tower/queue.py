"""
Queue Data Structure Implementation
Provides FIFO (First-In-First-Out) operations for:
- Player turn management and rotation
- Fair round-robin player scheduling
- Undo support for restoring previous turn order
"""

class Queue:
    """
    Native Python Queue implementation adhering to FIFO order.
    Used for round-robin player turns.
    """
    def __init__(self, name="PlayerQueue"):
        self.name = name
        self._items = []

    def enqueue(self, item):
        """Add an item to the rear of the queue."""
        self._items.append(item)

    def dequeue(self):
        """
        Remove and return the front item of the queue.
        Returns None if queue is empty.
        """
        if self.is_empty():
            return None
        return self._items.pop(0)

    def peek(self):
        """
        Return the front item without removing it.
        Returns None if queue is empty.
        """
        if self.is_empty():
            return None
        return self._items[0]

    def peek_next(self):
        """
        Return the second item in the queue (who is up next after the current turn).
        Returns None if fewer than 2 items.
        """
        if len(self._items) > 1:
            return self._items[1]
        elif len(self._items) == 1:
            return self._items[0]
        return None

    def is_empty(self):
        """Check if queue is empty."""
        return len(self._items) == 0

    def size(self):
        """Return total number of items in the queue."""
        return len(self._items)

    def display(self):
        """
        Return list of items ordered from front (current) to rear.
        """
        return list(self._items)

    def rotate(self):
        """
        Standard turn rotation:
        Dequeues the current player from the front and enqueues them at the rear.
        Returns the new front (the player whose turn is now active).
        """
        if len(self._items) <= 1:
            return self.peek()
        current = self.dequeue()
        self.enqueue(current)
        return self.peek()

    def rotate_backward(self):
        """
        Inverse rotation for undo:
        Pops the rear player and inserts them back at the front.
        """
        if len(self._items) <= 1:
            return self.peek()
        last = self._items.pop()
        self._items.insert(0, last)
        return self.peek()

    def remove(self, item):
        """Remove a specific item from the queue (e.g. player removal)."""
        if item in self._items:
            self._items.remove(item)
            return True
        return False

    def clear(self):
        """Clear the queue."""
        self._items.clear()

    def to_list(self):
        """Return raw list representation from front to rear."""
        return list(self._items)

    @classmethod
    def from_list(cls, items, name="PlayerQueue"):
        """Create and populate a queue from a list."""
        q = cls(name=name)
        q._items = list(items)
        return q

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __repr__(self):
        return f"Queue({self.name}, size={len(self._items)}, front={self.peek()})"
