from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QDrag
from PySide6.QtCore import Qt, QMimeData, QPoint, QRect
from constants import CELL_SIZE, GRID_LINE_COLOR, HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA, scale_pixmap

class GridTile(QLabel):
    """Tile that can be placed on grid and moved"""
    def __init__(self, file_path, parent_canvas):
        super().__init__(parent_canvas)
        self.file_path = file_path
        self.parent_canvas = parent_canvas
        self.drag_start_position = None

        self.update_pixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: white;")

    def update_pixmap(self):
        """Update pixmap based on current zoom level"""
        scaled_size = int(CELL_SIZE * self.parent_canvas.zoom_scale)
        pixmap = scale_pixmap(self.file_path, scaled_size, keep_aspect=False)
        self.setPixmap(pixmap)
        self.setFixedSize(scaled_size, scaled_size)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.raise_()  # Bring to front
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        
        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"TILE:{self.file_path}")
        drag.setMimeData(mime_data)

        # Set drag preview
        preview_pixmap = scale_pixmap(self.file_path, CELL_SIZE, keep_aspect=False)
        drag.setPixmap(preview_pixmap)
        drag.setHotSpot(preview_pixmap.rect().center())

        # Store reference to this tile and remove from canvas during drag
        self.parent_canvas.dragged_tile = self
        self.parent_canvas.remove_tile_at_position(self.pos())

        result = drag.exec(Qt.MoveAction)

        if result == Qt.IgnoreAction:
            # Drag cancelled, restore tile
            self.parent_canvas.add_tile_at_position(self, self.pos())

        # Clear the dragged tile reference
        self.parent_canvas.dragged_tile = None

class InfiniteGridCanvas(QWidget):
    """Infinite grid canvas for placing images"""
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.highlight_cell = None  # Cell to highlight during drag
        self.tiles = {}  # Dictionary: (grid_x, grid_y) -> GridTile
        self.dragged_tile = None  # Track tile being dragged for reuse

        # Zoom and pan state
        self.zoom_scale = 1.0
        self.MIN_ZOOM = 0.25  # Can zoom out to 25% - see whole grid
        self.MAX_ZOOM = 3.0   # Can zoom in to 300%
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.middle_mouse_pressed = False
        self.last_pan_pos = None
        
    def paintEvent(self, event):
        """Draw grid lines with zoom and pan transformations"""
        painter = QPainter(self)

        # Apply pan and zoom transformations
        painter.translate(self.pan_offset_x, self.pan_offset_y)
        painter.scale(self.zoom_scale, self.zoom_scale)

        painter.setPen(QPen(QColor(*GRID_LINE_COLOR), 1))

        # Calculate visible area in grid space, accounting for pan offset
        grid_start_x = int(-self.pan_offset_x / self.zoom_scale)
        grid_start_y = int(-self.pan_offset_y / self.zoom_scale)
        grid_end_x = int((self.width() - self.pan_offset_x) / self.zoom_scale)
        grid_end_y = int((self.height() - self.pan_offset_y) / self.zoom_scale)

        # Align to grid cell boundaries
        grid_start_x = (grid_start_x // CELL_SIZE) * CELL_SIZE
        grid_start_y = (grid_start_y // CELL_SIZE) * CELL_SIZE

        # Draw vertical lines
        for x in range(grid_start_x, grid_end_x + CELL_SIZE, CELL_SIZE):
            painter.drawLine(x, grid_start_y, x, grid_end_y)

        # Draw horizontal lines
        for y in range(grid_start_y, grid_end_y + CELL_SIZE, CELL_SIZE):
            painter.drawLine(grid_start_x, y, grid_end_x, y)

        # Highlight cell during drag
        if self.highlight_cell:
            grid_x, grid_y = self.highlight_cell
            if (grid_x, grid_y) not in self.tiles:  # Only highlight empty cells
                painter.setPen(QPen(QColor(*HIGHLIGHT_COLOR), 3))
                painter.setBrush(QColor(*HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA))
                rect = QRect(grid_x * CELL_SIZE, grid_y * CELL_SIZE,
                           CELL_SIZE, CELL_SIZE)
                painter.drawRect(rect)
    
    def wheelEvent(self, event):
        """Handle zoom with scroll wheel"""
        # Calculate zoom factor
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Calculate new zoom level
        new_zoom = self.zoom_scale * zoom_factor

        # Apply zoom limits
        if new_zoom < self.MIN_ZOOM:
            new_zoom = self.MIN_ZOOM
        elif new_zoom > self.MAX_ZOOM:
            new_zoom = self.MAX_ZOOM

        # Store old zoom for position adjustment
        old_zoom = self.zoom_scale
        self.zoom_scale = new_zoom

        # Adjust pan offset to zoom toward mouse position
        mouse_pos = event.position()
        self.pan_offset_x = mouse_pos.x() - (mouse_pos.x() - self.pan_offset_x) * (new_zoom / old_zoom)
        self.pan_offset_y = mouse_pos.y() - (mouse_pos.y() - self.pan_offset_y) * (new_zoom / old_zoom)

        # Update tile positions
        self.update_tile_positions()

        self.update()
        event.accept()

    def mousePressEvent(self, event):
        """Handle middle mouse button press for panning"""
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning"""
        if self.middle_mouse_pressed and self.last_pan_pos:
            delta = event.pos() - self.last_pan_pos
            self.pan_offset_x += delta.x()
            self.pan_offset_y += delta.y()
            self.last_pan_pos = event.pos()

            # Update tile positions
            self.update_tile_positions()

            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle middle mouse button release"""
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.last_pan_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def get_grid_position(self, pos):
        """Convert pixel position to grid coordinates, accounting for zoom and pan"""
        # Transform screen position to grid space
        x = (pos.x() - self.pan_offset_x) / self.zoom_scale
        y = (pos.y() - self.pan_offset_y) / self.zoom_scale
        grid_x = int(x // CELL_SIZE)
        grid_y = int(y // CELL_SIZE)
        return (grid_x, grid_y)

    def get_pixel_position(self, grid_pos):
        """Convert grid coordinates to pixel position, accounting for zoom and pan"""
        grid_x, grid_y = grid_pos
        x = grid_x * CELL_SIZE * self.zoom_scale + self.pan_offset_x
        y = grid_y * CELL_SIZE * self.zoom_scale + self.pan_offset_y
        return QPoint(int(x), int(y))

    def update_tile_positions(self):
        """Update all tile positions based on current zoom and pan"""
        for grid_pos, tile in self.tiles.items():
            pixel_pos = self.get_pixel_position(grid_pos)
            tile.move(pixel_pos)
            # Update tile pixmap and size based on zoom
            tile.update_pixmap()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        # Calculate which cell the mouse is over
        grid_pos = self.get_grid_position(event.position().toPoint())
        
        # Only highlight if cell is empty
        if grid_pos not in self.tiles:
            self.highlight_cell = grid_pos
        else:
            self.highlight_cell = None
        
        self.update()  # Trigger repaint
        event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        self.highlight_cell = None
        self.update()
    
    def dropEvent(self, event):
        grid_pos = self.get_grid_position(event.position().toPoint())

        # Only drop if cell is empty
        if grid_pos not in self.tiles:
            mime_text = event.mimeData().text()

            # Check if it's a tile being moved or new image from bank
            if mime_text.startswith("TILE:"):
                # Reuse the existing tile that's being moved
                if self.dragged_tile:
                    tile = self.dragged_tile
                    pixel_pos = self.get_pixel_position(grid_pos)
                    tile.move(pixel_pos)
                    tile.show()
                    self.tiles[grid_pos] = tile
                    event.acceptProposedAction()
            else:
                # New image from bank - create new tile
                file_path = mime_text
                tile = GridTile(file_path, self)
                pixel_pos = self.get_pixel_position(grid_pos)
                tile.move(pixel_pos)
                tile.show()
                self.tiles[grid_pos] = tile
                event.acceptProposedAction()

        self.highlight_cell = None
        self.update()
    
    def remove_tile_at_position(self, pixel_pos):
        """Remove tile at pixel position"""
        grid_pos = self.get_grid_position(pixel_pos)
        if grid_pos in self.tiles:
            self.tiles[grid_pos].hide()
            del self.tiles[grid_pos]
    
    def add_tile_at_position(self, tile, pixel_pos):
        """Add tile back at position (for cancelled drags)"""
        grid_pos = self.get_grid_position(pixel_pos)
        self.tiles[grid_pos] = tile
        tile.show()
    
    def clear_all(self):
        """Remove all tiles"""
        for tile in self.tiles.values():
            tile.deleteLater()
        self.tiles.clear()
        self.update()

    def remove_tiles_by_path(self, file_path):
        """Remove all tiles with the given file path"""
        positions_to_remove = [pos for pos, tile in self.tiles.items()
                              if tile.file_path == file_path]
        for pos in positions_to_remove:
            self.tiles[pos].deleteLater()
            del self.tiles[pos]
        self.update()