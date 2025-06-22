import pygame # For pygame.Rect
# Assuming utils.py is in the same package 'world_structures'
from .utils import is_point_in_polygon as util_is_point_in_polygon

class Zone:
    """
    Represents a geographical zone in the world, defined by a polygon.
    """
    def __init__(self, name, polygon_points, ground_color, properties=None):
        """
        Initializes a Zone.

        Args:
            name (str): The name of the zone (e.g., "forest", "kingdom").
            polygon_points (list of tuple): A list of (x, y) tuples defining the zone's boundary.
            ground_color (tuple): The RGB color for the zone's ground.
            properties (dict, optional): Additional properties for the zone. Defaults to None.
        """
        self.name = name
        self.polygon_points = polygon_points if polygon_points else []
        self.ground_color = ground_color
        self.properties = properties if properties is not None else {}

        if self.polygon_points and len(self.polygon_points) >= 3:
            min_x = min(p[0] for p in self.polygon_points)
            max_x = max(p[0] for p in self.polygon_points)
            min_y = min(p[1] for p in self.polygon_points)
            max_y = max(p[1] for p in self.polygon_points)
            self.bounds = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
        else:
            self.bounds = pygame.Rect(0,0,0,0) # Invalid or empty polygon

    def is_point_inside(self, point):
        """
        Checks if a given point is inside this zone's polygon.

        Args:
            point (tuple): The (x, y) coordinates of the point to check.

        Returns:
            bool: True if the point is inside the zone, False otherwise.
        """
        if not self.polygon_points or len(self.polygon_points) < 3:
            return False # Cannot be inside an invalid or empty polygon
        return util_is_point_in_polygon(point, self.polygon_points)