import pygame
import math

# --- Geometry Helpers ---
def is_point_in_polygon(point, polygon_vertices):
    """Checks if a point is inside a given polygon using the Ray Casting algorithm."""
    x, y = point; n = len(polygon_vertices);
    if n < 3: return False
    inside = False; p1x, p1y = polygon_vertices[0]
    for i in range(n + 1):
        p2x, p2y = polygon_vertices[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y == p2y: # Horizontal edge
                 if y == p1y and x >= min(p1x, p2x) and x <= max(p1x, p2x):
                      # Point on horizontal edge check (can decide if inclusive)
                      return True # Let's consider points on edges inside
            else:
                 xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                 if p1x == p2x: # Vertical edge
                      if x <= p1x: inside = not inside
                 elif x <= xinters: inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def point_segment_distance_sq(px, py, ax, ay, bx, by):
    """Calculates the squared distance from a point (px, py) to a line segment (ax, ay) -> (bx, by)."""
    seg_len_sq = (bx - ax)**2 + (by - ay)**2
    if seg_len_sq == 0: return (px - ax)**2 + (py - ay)**2 # Segment is a point
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / seg_len_sq
    t = max(0, min(1, t)) # Clamp t to [0, 1]
    closest_x = ax + t * (bx - ax); closest_y = ay + t * (by - ay)
    dist_sq = (px - closest_x)**2 + (py - closest_y)**2
    return dist_sq

# --- Camera Helpers ---
def apply_camera_to_point(world_x, world_y, camera_x, camera_y):
    """Converts world coordinates to screen coordinates based on camera position."""
    return int(world_x - camera_x), int(world_y - camera_y)

def apply_camera_to_rect(world_rect, camera_x, camera_y):
    """Moves a world Rect to its screen position based on camera."""
    return world_rect.move(-camera_x, -camera_y)