"""Constants and utility functions for the Tiler application"""
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

# Size constants
CELL_SIZE = 60
THUMBNAIL_WIDTH = 85
LARGE_VIEW_WIDTH = 800
DRAG_PREVIEW_SIZE = 100

# Grid dimensions
GRID_ROWS = 20
GRID_COLUMNS = 20

# Style constants
SELECTION_BORDER_COLOR = "#4A90E2"  # Bank selection color
GRID_TILE_SELECTION_COLOR = "#2E7BD6"  # Grid tile selection color (darker blue)
SELECTION_BORDER_WIDTH = 3
GRID_LINE_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (74, 144, 226)
HIGHLIGHT_ALPHA = 30

def scale_pixmap(file_path, width, keep_aspect=True):
    """Load and scale a pixmap to specified width

    Args:
        file_path: Path to image file
        width: Target width
        keep_aspect: Whether to maintain aspect ratio

    Returns:
        Scaled QPixmap
    """
    pixmap = QPixmap(file_path)
    if keep_aspect:
        return pixmap.scaledToWidth(width, Qt.SmoothTransformation)
    else:
        return pixmap.scaled(width, width, Qt.KeepAspectRatio, Qt.SmoothTransformation)
