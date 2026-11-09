"""
Block Entity
Represents an individual physical wooden block in the Tumble Tower.
Contains metadata, positional state, wood color tone, and status tracking.
"""

WOOD_PALETTES = [
    {"name": "Natural Oak", "hex": "#D8C6AD", "dark": "#8A7359", "grain": "rgba(92, 73, 56, 0.12)"},
    {"name": "Honey Maple", "hex": "#E0CEB5", "dark": "#9C8368", "grain": "rgba(92, 73, 56, 0.10)"},
    {"name": "Golden Birch", "hex": "#E8D9C5", "dark": "#B39878", "grain": "rgba(92, 73, 56, 0.08)"},
    {"name": "Rich Walnut", "hex": "#C2AC91", "dark": "#755B42", "grain": "rgba(92, 73, 56, 0.16)"},
    {"name": "Red Cedar", "hex": "#C8A882", "dark": "#7E5B3D", "grain": "rgba(92, 73, 56, 0.14)"},
    {"name": "Deep Mahogany", "hex": "#B59475", "dark": "#5C412C", "grain": "rgba(92, 73, 56, 0.20)"},
]

POSITION_NAMES = {0: "Left", 1: "Center", 2: "Right"}

class Block:
    """
    Tumble Tower Block model.
    """
    def __init__(self, block_id, number, color, level, position, status="in_tower", hex_color=None, dark_hex=None):
        self.id = str(block_id)
        self.number = int(number)
        self.color = str(color)
        self.level = int(level)
        self.position = int(position)  # 0: Left, 1: Middle/Center, 2: Right
        self.status = str(status)      # "in_tower", "selected", "removed", "placed"
        
        # Color tones for rendering natural wood blocks
        palette_match = next((p for p in WOOD_PALETTES if p["name"].lower() == color.lower()), None)
        if palette_match:
            self.hex_color = hex_color or palette_match["hex"]
            self.dark_hex = dark_hex or palette_match["dark"]
        else:
            self.hex_color = hex_color or "#D8C6AD"
            self.dark_hex = dark_hex or "#8A7359"

    @property
    def position_name(self):
        return POSITION_NAMES.get(self.position, f"Pos {self.position}")

    def matches_query(self, query_type, query_val):
        """
        Check whether this block satisfies search criteria.
        query_type: 'id', 'number', 'color', 'level'
        """
        val_str = str(query_val).strip().lower()
        if not val_str:
            return True
            
        if query_type == "id":
            return val_str in self.id.lower()
        elif query_type == "number":
            return str(self.number) == val_str
        elif query_type == "color":
            return val_str in self.color.lower()
        elif query_type == "level":
            return str(self.level) == val_str
        elif query_type == "all":
            return (val_str in self.id.lower() or 
                    str(self.number) == val_str or 
                    val_str in self.color.lower() or 
                    str(self.level) == val_str)
        return False

    def to_dict(self):
        """Serialize block to dictionary."""
        return {
            "id": self.id,
            "number": self.number,
            "color": self.color,
            "level": self.level,
            "position": self.position,
            "status": self.status,
            "hex_color": self.hex_color,
            "dark_hex": self.dark_hex,
            "position_name": self.position_name
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize dictionary into Block object."""
        return cls(
            block_id=data.get("id"),
            number=data.get("number"),
            color=data.get("color"),
            level=data.get("level"),
            position=data.get("position"),
            status=data.get("status", "in_tower"),
            hex_color=data.get("hex_color"),
            dark_hex=data.get("dark_hex")
        )

    def __repr__(self):
        return f"Block(id={self.id}, num={self.number}, lvl={self.level}, pos={self.position}, status={self.status})"
