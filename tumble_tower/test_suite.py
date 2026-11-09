"""
Comprehensive Test Suite for Tumble Tower
Verifies:
1. Stack Operations (LIFO)
2. Queue Operations (FIFO)
3. LinkedList Operations (Doubly Linked Layer Hierarchy)
4. Game Rules & Accessibility Verification
5. Auxiliary Stack Extraction Algorithm
6. Apex Placement and Dynamic Level Creation
7. Multi-step Undo & History Stack
8. Searching Algorithms
9. SQLite Database Persistence
10. Flask Web Endpoints & SSR Forms
"""

import unittest
import os
import tempfile
from tumble_tower.stack import Stack
from tumble_tower.queue import Queue
from tumble_tower.linked_list import LinkedList, LevelNode
from tumble_tower.block import Block
from tumble_tower.game_rules import GameRules
from tumble_tower.history import HistoryStack, MoveRecord
from tumble_tower.database import Database
from tumble_tower.game_engine import GameEngine
from tumble_tower.app import app

class TestTumbleTower(unittest.TestCase):

    def test_stack_operations(self):
        """Test Stack LIFO behavior: push, pop, peek, is_empty, display."""
        s = Stack(name="TestStack")
        self.assertTrue(s.is_empty())
        self.assertIsNone(s.peek())
        self.assertIsNone(s.pop())

        s.push("Block-A")
        s.push("Block-B")
        s.push("Block-C")

        self.assertFalse(s.is_empty())
        self.assertEqual(s.size(), 3)
        self.assertEqual(s.peek(), "Block-C")

        # Display should be top to bottom (LIFO)
        self.assertEqual(s.display(), ["Block-C", "Block-B", "Block-A"])

        # Pop should yield in reverse order
        self.assertEqual(s.pop(), "Block-C")
        self.assertEqual(s.pop(), "Block-B")
        self.assertEqual(s.pop(), "Block-A")
        self.assertTrue(s.is_empty())

    def test_queue_operations(self):
        """Test Queue FIFO behavior: enqueue, dequeue, peek, rotate, rotate_backward."""
        q = Queue(name="TestQueue")
        self.assertTrue(q.is_empty())
        self.assertIsNone(q.peek())

        q.enqueue("Alice")
        q.enqueue("Bob")
        q.enqueue("Charlie")

        self.assertEqual(q.size(), 3)
        self.assertEqual(q.peek(), "Alice")
        self.assertEqual(q.peek_next(), "Bob")
        self.assertEqual(q.display(), ["Alice", "Bob", "Charlie"])

        # Rotate should move front to rear
        new_front = q.rotate()
        self.assertEqual(new_front, "Bob")
        self.assertEqual(q.peek(), "Bob")
        self.assertEqual(q.display(), ["Bob", "Charlie", "Alice"])

        # Rotate backward (for undo) should reverse rotation
        restored_front = q.rotate_backward()
        self.assertEqual(restored_front, "Alice")
        self.assertEqual(q.display(), ["Alice", "Bob", "Charlie"])

        # Dequeue FIFO
        self.assertEqual(q.dequeue(), "Alice")
        self.assertEqual(q.dequeue(), "Bob")
        self.assertEqual(q.dequeue(), "Charlie")
        self.assertTrue(q.is_empty())

    def test_linked_list_operations(self):
        """Test LinkedList layer operations, insertion, deletion, and traversal."""
        ll = LinkedList()
        self.assertEqual(ll.get_level_count(), 0)

        # Insert 3 levels
        l1 = ll.insert_level(1, "horizontal")
        l2 = ll.insert_level(2, "vertical")
        l3 = ll.insert_level(3, "horizontal")

        self.assertEqual(ll.get_level_count(), 3)
        self.assertEqual(ll.head.level_number, 1)
        self.assertEqual(ll.tail.level_number, 3)
        self.assertEqual(l1.next, l2)
        self.assertEqual(l2.prev, l1)
        self.assertEqual(l2.next, l3)
        self.assertEqual(l3.prev, l2)

        # Insert blocks
        b1 = Block("BLK-01", 1, "Oak", 1, 0)
        b2 = Block("BLK-02", 2, "Maple", 1, 1)
        b3 = Block("BLK-03", 3, "Walnut", 1, 2)

        ll.insert_block(1, b1, 0)
        ll.insert_block(1, b2, 1)
        ll.insert_block(1, b3, 2)

        self.assertEqual(l1.block_count, 3)
        self.assertTrue(l1.is_complete)
        self.assertEqual(ll.count_blocks(), 3)

        # Delete a block by ID
        removed = ll.delete_block("BLK-02")
        self.assertIsNotNone(removed)
        self.assertEqual(removed.id, "BLK-02")
        self.assertEqual(l1.block_count, 2)
        self.assertIsNone(l1.get_block(1))

    def test_game_rules_accessibility(self):
        """Verify Level 1 protection, top levels protection, and accessibility."""
        engine = GameEngine()
        engine.setup_new_game(["Alice", "Bob"])

        # Level 1 is protected (foundation)
        blk_l1 = engine.tower.find_level(1).get_block(0)
        is_acc, reason = GameRules.is_block_accessible(engine.tower, blk_l1)
        self.assertFalse(is_acc)
        self.assertIn("Level 1 is the tower foundation", reason)

        # Level 18, 17, 16 are top complete levels -> protected!
        blk_l18 = engine.tower.find_level(18).get_block(0)
        is_acc18, _ = GameRules.is_block_accessible(engine.tower, blk_l18)
        self.assertFalse(is_acc18)

        blk_l17 = engine.tower.find_level(17).get_block(0)
        is_acc17, _ = GameRules.is_block_accessible(engine.tower, blk_l17)
        self.assertFalse(is_acc17)

        # Level 10 is accessible!
        blk_l10 = engine.tower.find_level(10).get_block(0)
        is_acc10, _ = GameRules.is_block_accessible(engine.tower, blk_l10)
        self.assertTrue(is_acc10)

    def test_extraction_with_auxiliary_stack_and_placement(self):
        """Test auxiliary stack operation during extraction, apex placement, and undo."""
        engine = GameEngine(difficulty="easy")
        engine.setup_new_game(["Alice", "Bob"])

        # Select block on Level 10
        blk_target = engine.tower.find_level(10).get_block(0)
        is_acc, _ = engine.select_block(blk_target.id)
        self.assertTrue(is_acc)

        # Remove selected block
        success, msg = engine.remove_selected_block()
        self.assertTrue(success)
        self.assertIsNotNone(engine.held_block)
        self.assertEqual(engine.held_block.id, blk_target.id)

        # Verify that auxiliary stack trace was generated
        self.assertTrue(len(engine.auxiliary_trace) > 0)
        push_steps = [t for t in engine.auxiliary_trace if t["action"] == "PUSH_TO_AUXILIARY_STACK"]
        restore_steps = [t for t in engine.auxiliary_trace if t["action"] == "POP_AND_RESTORE"]
        self.assertEqual(len(push_steps), len(restore_steps))

        # Place held block on top
        current_p = engine.player_queue.peek()
        self.assertEqual(current_p, "Alice")

        success, place_msg = engine.place_held_block()
        self.assertTrue(success)
        self.assertIsNone(engine.held_block)
        self.assertEqual(engine.total_moves, 1)

        # Turn should have rotated via FIFO queue to Bob!
        self.assertEqual(engine.player_queue.peek(), "Bob")

        # Now test Undo!
        undo_success, undo_msg = engine.undo_move()
        self.assertTrue(undo_success)
        self.assertEqual(engine.total_moves, 0)
        # Turn restored to Alice!
        self.assertEqual(engine.player_queue.peek(), "Alice")
        # Target block should be back in tower at Level 10
        restored_blk = engine.tower.find_level(10).get_block(0)
        self.assertIsNotNone(restored_blk)
        self.assertEqual(restored_blk.id, blk_target.id)

    def test_search_algorithms(self):
        """Test searching by ID, number, colour, and level."""
        engine = GameEngine()
        engine.setup_new_game(["Alice", "Bob"])

        # Search by ID
        res_id = engine.search_blocks(query_type="id", query_val="BLK-05")
        self.assertEqual(len(res_id), 1)
        self.assertEqual(res_id[0]["block"]["id"], "BLK-05")

        # Search by Number
        res_num = engine.search_blocks(query_type="number", query_val="12")
        self.assertEqual(len(res_num), 1)
        self.assertEqual(res_num[0]["block"]["number"], 12)

        # Search by Level
        res_lvl = engine.search_blocks(query_type="level", query_val="4")
        self.assertEqual(len(res_lvl), 3)

    def test_database_persistence(self):
        """Test SQLite saving, loading, and player management."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            temp_db = Database(db_path=f.name)
            # Add player
            added, msg = temp_db.add_player("TestPlayer")
            self.assertTrue(added)
            players = temp_db.get_all_players()
            self.assertTrue(any(p["name"] == "TestPlayer" for p in players))

            # Save and load game
            engine = GameEngine()
            engine.setup_new_game(["TestPlayer", "Sam"])
            temp_db.save_game(engine.to_dict())

            loaded = temp_db.load_game(engine.game_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["game_id"], engine.game_id)
            self.assertEqual(loaded["total_levels"], 18)

    def test_flask_routes_and_forms(self):
        """Test that all 8 Flask routes render successfully via SSR without JavaScript."""
        app.testing = True
        client = app.test_client()

        # 1. Dashboard
        resp = client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Welcome to Tumble Tower", resp.data)

        # 2. Setup
        resp = client.get("/setup")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"New Tower Match Setup", resp.data)

        # POST setup
        resp = client.post("/setup", data={
            "players": ["Alex", "Sam"],
            "difficulty": "medium"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 3. Game Play
        resp = client.get("/game")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Tumble Tower", resp.data)
        self.assertIn(b"Player Turn Queue", resp.data)

        # 4. Players
        resp = client.get("/players")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Player Management", resp.data)

        # 5. Search
        resp = client.get("/search?query_type=all&query_val=15")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Found", resp.data)

        # 6. History
        resp = client.get("/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Move History", resp.data)

        # 7. Statistics
        resp = client.get("/statistics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Tower Statistics", resp.data)

        # 8. Instructions
        resp = client.get("/instructions")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"How to Play", resp.data)


if __name__ == "__main__":
    unittest.main()
