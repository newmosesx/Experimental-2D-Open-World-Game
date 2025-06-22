import pygame
from world_structures.world_constants import QT_MAX_DEPTH

# --- Quadtree Implementation --- (Unchanged)
class QuadtreeNode:
    def __init__(self, boundary, capacity, depth=0):
        self.boundary = pygame.Rect(boundary); self.capacity = capacity; self.items = []; self.depth = depth
        self.divided = False; self.north_west = None; self.north_east = None; self.south_west = None; self.south_east = None
    def subdivide(self):
        x, y, w, h = self.boundary; hw, hh = w / 2, h / 2
        if hw < 1 or hh < 1: return # Prevent subdividing too small
        nw = pygame.Rect(x, y, hw, hh); ne = pygame.Rect(x + hw, y, hw, hh)
        sw = pygame.Rect(x, y + hh, hw, hh); se = pygame.Rect(x + hw, y + hh, hw, hh)
        self.north_west = QuadtreeNode(nw, self.capacity, self.depth + 1); self.north_east = QuadtreeNode(ne, self.capacity, self.depth + 1)
        self.south_west = QuadtreeNode(sw, self.capacity, self.depth + 1); self.south_east = QuadtreeNode(se, self.capacity, self.depth + 1)
        self.divided = True; items_to_keep = []; items_to_redistribute = self.items; self.items = []
        for item in items_to_redistribute:
            inserted = False
            # Determine if item is a rect or point-like tuple
            item_rect = item if isinstance(item, pygame.Rect) else pygame.Rect(item[0]-1, item[1]-1, 2, 2)
            if self.north_west.insert(item): inserted = True
            elif self.north_east.insert(item): inserted = True
            elif self.south_west.insert(item): inserted = True
            elif self.south_east.insert(item): inserted = True
            if not inserted: # If it didn't fit squarely in a child, keep it here
                items_to_keep.append(item)
        self.items = items_to_keep # Add items that span subdivisions back to the current node
    def insert(self, item):
        # Determine if item is a rect or point-like tuple
        item_rect = item if isinstance(item, pygame.Rect) else pygame.Rect(item[0]-1, item[1]-1, 2, 2) # Treat tuples as small rects for collision
        if not self.boundary.colliderect(item_rect): return False
        if self.divided:
            if self.north_west.insert(item): return True
            if self.north_east.insert(item): return True
            if self.south_west.insert(item): return True
            if self.south_east.insert(item): return True
            # If it couldn't fit into any subdivision but intersects boundary, keep it here
            self.items.append(item); return True
        if len(self.items) < self.capacity: self.items.append(item); return True
        if self.depth < QT_MAX_DEPTH: self.subdivide(); return self.insert(item)
        else: self.items.append(item); return True # Reached max depth, add here
    def query(self, range_rect):
        found_items = [];
        if not self.boundary.colliderect(range_rect): return found_items
        for item in self.items:
            item_rect = item if isinstance(item, pygame.Rect) else pygame.Rect(item[0]-1, item[1]-1, 2, 2)
            if range_rect.colliderect(item_rect): found_items.append(item)
        if self.divided:
            found_items.extend(self.north_west.query(range_rect)); found_items.extend(self.north_east.query(range_rect))
            found_items.extend(self.south_west.query(range_rect)); found_items.extend(self.south_east.query(range_rect))
        return found_items


# --- Helper Functions ---
# generate_wall_rects: Remains unchanged for COLLISION.
def generate_wall_rects(vertices, thickness, gate_segment_index, gate_point1, gate_point2):
    rects = []; num_vertices = len(vertices); step = thickness * 0.8 # Use step smaller than thickness
    for i in range(num_vertices):
        p1_v = pygame.math.Vector2(vertices[i]); p2_v = pygame.math.Vector2(vertices[(i + 1) % num_vertices])
        if i == gate_segment_index and gate_point1 and gate_point2:
            # Part 1: From segment start (p1_v) to gate start (gate_point1)
            vec1 = gate_point1 - p1_v; len1 = vec1.length()
            if len1 > 1: # Avoid division by zero / zero vector
                dir1 = vec1.normalize(); num_steps1 = int(len1 / step)
                for j in range(num_steps1 + 1):
                    # Place collision rect centered on the path
                    center_pos = p1_v + dir1 * min(j * step, len1)
                    rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
            # Part 2: From gate end (gate_point2) to segment end (p2_v)
            vec2 = p2_v - gate_point2; len2 = vec2.length()
            if len2 > 1:
                dir2 = vec2.normalize(); num_steps2 = int(len2 / step)
                for j in range(num_steps2 + 1):
                    # Place collision rect centered on the path, starting from gate_point2
                    center_pos = gate_point2 + dir2 * min(j * step, len2)
                    rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
            continue # Move to the next segment
        # --- Handle Normal Segment Collision Rects ---
        segment_vec = p2_v - p1_v; seg_len = segment_vec.length()
        if seg_len < 1: continue # Skip zero-length segments
        seg_dir = segment_vec.normalize(); num_steps = int(seg_len / step)
        for j in range(num_steps + 1):
            center_pos = p1_v + seg_dir * min(j * step, seg_len)
            rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
    return rects