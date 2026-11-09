"""
Game Rules and Physics Validation Engine
Enforces:
- Block accessibility validation
- Bottom level protection (Level 1 cannot be removed)
- Top levels protection (Top incomplete and top 3 complete levels cannot be removed)
- Deterministic Tower Stability and Center-of-Mass (CoM) collapse calculation
"""

class GameRules:
    """
    Deterministic rule engine for Tumble Tower moves and structural physics.
    """

    @staticmethod
    def get_protected_top_levels(tower_linked_list):
        """
        Calculates which top levels are protected from removal:
        - The current topmost incomplete level (where blocks are currently being added).
        - The 3 highest complete levels below or including top.
        """
        top_node = tower_linked_list.get_top_level()
        if not top_node:
            return set()

        protected = set()
        curr = top_node
        complete_count = 0

        while curr:
            # If it's the very top level and incomplete, it's protected
            if curr == top_node and not curr.is_complete:
                protected.add(curr.level_number)
            elif curr.is_complete:
                if complete_count < 3:
                    protected.add(curr.level_number)
                    complete_count += 1
                else:
                    break
            else:
                # Incomplete level near top
                if complete_count < 3:
                    protected.add(curr.level_number)
            curr = curr.prev

        return protected

    @classmethod
    def is_block_accessible(cls, tower_linked_list, block):
        """
        Check if a specific block can be legally removed.
        Returns: (is_valid: bool, reason_or_message: str)
        """
        if not block:
            return False, "No block selected."

        if block.status != "in_tower":
            return False, f"Block {block.id} is already {block.status}."

        level_num = block.level
        level_node = tower_linked_list.find_level(level_num)

        if not level_node:
            return False, f"Level {level_num} does not exist in the tower."

        # Rule 1: The bottom level (Level 1) cannot be removed
        if level_num == 1:
            return False, "Rule violation: Level 1 is the tower foundation and cannot be removed."

        # Rule 2: Top three complete levels (and topmost incomplete level) cannot be removed
        protected_levels = cls.get_protected_top_levels(tower_linked_list)
        if level_num in protected_levels:
            return False, (
                f"Rule violation: Level {level_num} is among the protected top levels. "
                "Blocks cannot be extracted from the top incomplete level or the top 3 complete levels."
            )

        # Rule 3: Cannot remove the last remaining block from a level
        if level_node.block_count <= 1:
            return False, (
                f"Rule violation: Block {block.id} is the only remaining support on Level {level_num}. "
                "Removing it would leave the upper tower with zero support."
            )

        return True, "Block is accessible and can be safely extracted."

    @staticmethod
    def calculate_stability(tower_linked_list, difficulty="medium"):
        """
        Computes deterministic center of gravity and support base for every layer.
        Difficulty thresholds:
        - 'easy':   higher tolerance (0.65 margin)
        - 'medium': standard balance (0.42 margin)
        - 'hard':   strict balance (0.22 margin)

        Returns:
            dict with keys:
            - 'status': 'stable' | 'wobbly' | 'critical' | 'collapsed'
            - 'stability_percentage': int (0 to 100)
            - 'max_imbalance': float
            - 'collapsed_level': int or None
            - 'reason': str
        """
        tolerance_map = {
            "easy": 0.65,
            "medium": 0.42,
            "hard": 0.22
        }
        tolerance = tolerance_map.get(str(difficulty).lower(), 0.42)

        # Map levels and compute block weights
        # Position mapping: Left = -1.0, Center = 0.0, Right = 1.0
        pos_values = {0: -1.0, 1: 0.0, 2: 1.0}

        all_levels = tower_linked_list.traverse(from_top=False) # bottom to top
        if not all_levels:
            return {
                "status": "stable",
                "stability_percentage": 100,
                "max_imbalance": 0.0,
                "collapsed_level": None,
                "reason": "Tower is empty or initialized."
            }

        max_imbalance = 0.0
        critical_threshold = tolerance * 0.75
        wobbly_threshold = tolerance * 0.40

        for i, node in enumerate(all_levels):
            # Check if an intermediate level with upper blocks has 0 blocks
            upper_blocks = []
            for upper_node in all_levels[i+1:]:
                for b in upper_node.blocks:
                    if b:
                        upper_blocks.append(b)

            if node.block_count == 0 and len(upper_blocks) > 0:
                return {
                    "status": "collapsed",
                    "stability_percentage": 0,
                    "max_imbalance": 999.0,
                    "collapsed_level": node.level_number,
                    "reason": f"Level {node.level_number} was completely hollowed out beneath {len(upper_blocks)} upper blocks."
                }

            if not upper_blocks or node.block_count == 0:
                continue

            # Calculate upper center of mass relative to level center
            upper_com = sum(pos_values[b.position] for b in upper_blocks) / len(upper_blocks)

            # Calculate support base bounds of current level
            active_positions = [pos_values[b.position] for b in node.blocks if b]
            min_support = min(active_positions)
            max_support = max(active_positions)

            # Single center block has tight support [-0.35, +0.35]
            # Single side block has tight support around its side
            if len(active_positions) == 1:
                single_pos = active_positions[0]
                support_min = single_pos - 0.35
                support_max = single_pos + 0.35
            else:
                support_min = min_support - 0.15
                support_max = max_support + 0.15

            # Calculate distance of upper CoM from valid support base
            overhang = 0.0
            if upper_com < support_min:
                overhang = support_min - upper_com
            elif upper_com > support_max:
                overhang = upper_com - support_max

            if overhang > max_imbalance:
                max_imbalance = overhang

            if overhang > tolerance:
                return {
                    "status": "collapsed",
                    "stability_percentage": 0,
                    "max_imbalance": round(max_imbalance, 3),
                    "collapsed_level": node.level_number,
                    "reason": (
                        f"Center of mass (CoM={upper_com:+.2f}) tilted past Level {node.level_number}'s "
                        f"support base [{support_min:+.2f}, {support_max:+.2f}] with overhang {overhang:.2f} "
                        f"(exceeded {difficulty} tolerance of {tolerance:.2f})."
                    )
                }

        # Check adjacent single-block opposite cantilever hazard
        for i in range(len(all_levels) - 1):
            n1 = all_levels[i]
            n2 = all_levels[i+1]
            if n1.block_count == 1 and n2.block_count == 1:
                b1_pos = [b.position for b in n1.blocks if b][0]
                b2_pos = [b.position for b in n2.blocks if b][0]
                # If one is left and the other is right
                if (b1_pos == 0 and b2_pos == 2) or (b1_pos == 2 and b2_pos == 0):
                    add_imbalance = 0.30
                    max_imbalance = max(max_imbalance, add_imbalance)
                    if difficulty == "hard":
                        return {
                            "status": "collapsed",
                            "stability_percentage": 0,
                            "max_imbalance": round(max_imbalance, 3),
                            "collapsed_level": n2.level_number,
                            "reason": f"Opposite-side single block pivot on Levels {n1.level_number} and {n2.level_number} caused cantilever shear collapse."
                        }

        # Determine status
        if max_imbalance > critical_threshold:
            status = "critical"
            stability_pct = max(10, int(100 - (max_imbalance / tolerance) * 90))
        elif max_imbalance > wobbly_threshold:
            status = "wobbly"
            stability_pct = max(35, int(100 - (max_imbalance / tolerance) * 75))
        else:
            status = "stable"
            stability_pct = max(75, int(100 - (max_imbalance / tolerance) * 40))

        return {
            "status": status,
            "stability_percentage": stability_pct,
            "max_imbalance": round(max_imbalance, 3),
            "collapsed_level": None,
            "reason": f"Tower is {status.upper()} (imbalance index: {max_imbalance:.2f}/{tolerance:.2f})."
        }
