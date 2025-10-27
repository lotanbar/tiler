from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QDrag, QFont
from PySide6.QtCore import Qt, QMimeData, QPoint, QRect, QTimer
from constants import CELL_SIZE, GRID_LINE_COLOR, HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA, scale_pixmap, GRID_ROWS, GRID_COLUMNS, GRID_TILE_SELECTION_COLOR, SELECTION_BORDER_WIDTH, DRAG_PREVIEW_SIZE
import json

class GridTile(QLabel):
    """Tile that can be placed on grid and moved"""
    def __init__(self, file_path, parent_canvas, viewer):
        super().__init__(parent_canvas)
        self.file_path = file_path
        self.parent_canvas = parent_canvas
        self.viewer = viewer
        self.drag_start_position = None
        self.is_dragging = False
        self.selected = False

        self.update_pixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: white;")

    def update_pixmap(self):
        """Update pixmap based on current zoom level"""
        scaled_size = int(CELL_SIZE * self.parent_canvas.zoom_scale)
        pixmap = scale_pixmap(self.file_path, scaled_size, keep_aspect=False)
        self.setPixmap(pixmap)
        self.setFixedSize(scaled_size, scaled_size)

    def set_selected(self, selected):
        """Set selection state and update visual styling"""
        self.selected = selected
        if selected:
            self.setStyleSheet(f"background-color: white; border: {SELECTION_BORDER_WIDTH}px solid {GRID_TILE_SELECTION_COLOR};")
        else:
            self.setStyleSheet("background-color: white;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = False
            self.raise_()  # Bring to front
        elif event.button() == Qt.RightButton:
            self.viewer.show_large_image(self.file_path)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Mark that we're dragging
        self.is_dragging = True

        # Get grid position of this tile
        grid_pos = self.parent_canvas.get_grid_position(self.pos())

        # Check if dragging multiple selected tiles
        if (self.viewer and
            grid_pos in self.viewer.selected_grid_tiles and
            len(self.viewer.selected_grid_tiles) > 1):

            # Multi-tile drag - get all selected tiles sorted by position (row, col)
            selected_positions = sorted(list(self.viewer.selected_grid_tiles),
                                       key=lambda p: (p[1], p[0]))  # Sort by row, then column
            selected_paths = [self.parent_canvas.tiles[pos].file_path
                            for pos in selected_positions]

            # Start drag operation
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(json.dumps({"multi": selected_paths}))
            drag.setMimeData(mime_data)

            # Set drag preview with count indicator
            preview_pixmap = scale_pixmap(self.file_path, DRAG_PREVIEW_SIZE, keep_aspect=False)
            painter = QPainter(preview_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw badge background
            badge_size = 30
            painter.setBrush(Qt.red)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(preview_pixmap.width() - badge_size, 0, badge_size, badge_size)

            # Draw count text
            painter.setPen(Qt.white)
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(preview_pixmap.width() - badge_size, 0, badge_size, badge_size,
                           Qt.AlignCenter, str(len(selected_paths)))
            painter.end()

            drag.setPixmap(preview_pixmap)
            drag.setHotSpot(preview_pixmap.rect().center())

            # Store tiles and remove all selected tiles during drag
            self.parent_canvas.dragged_tiles = {}  # Map: grid_pos -> tile
            for pos in selected_positions:
                tile = self.parent_canvas.tiles[pos]
                self.parent_canvas.dragged_tiles[pos] = tile
                tile.hide()
                del self.parent_canvas.tiles[pos]

            result = drag.exec(Qt.MoveAction)

            # If drag cancelled, restore all tiles
            if result == Qt.IgnoreAction:
                for pos, tile in self.parent_canvas.dragged_tiles.items():
                    self.parent_canvas.tiles[pos] = tile
                    tile.show()
                self.parent_canvas.dragged_tiles = None
            elif result == Qt.MoveAction:
                # Drop succeeded
                # Clear selection first
                if self.viewer:
                    self.viewer.clear_grid_selection()

                # DON'T delete tiles from here - let the canvas handle cleanup
                # Schedule cleanup to happen from canvas, not from self
                QTimer.singleShot(0, self.parent_canvas.cleanup_multi_drag)

        else:
            # Single tile drag
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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            # If plain click without drag and no modifiers
            if not self.is_dragging:
                # Get grid position of this tile
                grid_pos = self.parent_canvas.get_grid_position(self.pos())

                if modifiers == Qt.ShiftModifier:
                    # Shift-click for range selection
                    self.viewer.select_grid_range(grid_pos)
                elif modifiers == Qt.NoModifier:
                    # Plain click toggles selection
                    self.viewer.toggle_grid_selection(grid_pos)

class InfiniteGridCanvas(QWidget):
    """Infinite grid canvas for placing images"""
    def __init__(self, viewer=None):
        super().__init__()
        self.viewer = viewer  # Reference to parent ImageViewer
        self.setAcceptDrops(True)
        self.highlight_cell = None  # Cell to highlight during drag
        self.highlight_cells = []  # Multiple cells to highlight for multi-image drag
        self.tiles = {}  # Dictionary: (grid_x, grid_y) -> GridTile
        self.dragged_tile = None  # Track single tile being dragged for reuse
        self.dragged_tiles = None  # Track multiple tiles being dragged (dict: grid_pos -> tile)

        # Grid dimensions
        self.grid_rows = GRID_ROWS
        self.grid_columns = GRID_COLUMNS

        # Zoom and pan state
        self.zoom_scale = 1.0
        self.MIN_ZOOM = 0.25  # Can zoom out to 25% - see whole grid
        self.MAX_ZOOM = 3.0   # Can zoom in to 300%
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.middle_mouse_pressed = False
        self.last_pan_pos = None

        # Marquee selection state
        self.marquee_selecting = False
        self.marquee_start_pos = None
        self.marquee_current_pos = None
        
    def paintEvent(self, event):
        """Draw grid lines with zoom and pan transformations"""
        painter = QPainter(self)

        # Apply pan and zoom transformations
        painter.translate(self.pan_offset_x, self.pan_offset_y)
        painter.scale(self.zoom_scale, self.zoom_scale)

        painter.setPen(QPen(QColor(*GRID_LINE_COLOR), 1))

        # Calculate grid boundaries
        max_grid_x = self.grid_columns * CELL_SIZE
        max_grid_y = self.grid_rows * CELL_SIZE

        # Calculate visible area in grid space, accounting for pan offset
        grid_start_x = int(-self.pan_offset_x / self.zoom_scale)
        grid_start_y = int(-self.pan_offset_y / self.zoom_scale)
        grid_end_x = int((self.width() - self.pan_offset_x) / self.zoom_scale)
        grid_end_y = int((self.height() - self.pan_offset_y) / self.zoom_scale)

        # Clamp to grid boundaries
        grid_start_x = max(0, (grid_start_x // CELL_SIZE) * CELL_SIZE)
        grid_start_y = max(0, (grid_start_y // CELL_SIZE) * CELL_SIZE)
        grid_end_x = min(max_grid_x, grid_end_x)
        grid_end_y = min(max_grid_y, grid_end_y)

        # Draw vertical lines
        for x in range(grid_start_x, grid_end_x + CELL_SIZE, CELL_SIZE):
            if x <= max_grid_x:
                painter.drawLine(x, grid_start_y, x, grid_end_y)

        # Draw horizontal lines
        for y in range(grid_start_y, grid_end_y + CELL_SIZE, CELL_SIZE):
            if y <= max_grid_y:
                painter.drawLine(grid_start_x, y, grid_end_x, y)

        # Highlight cells during drag
        cells_to_highlight = self.highlight_cells if self.highlight_cells else ([self.highlight_cell] if self.highlight_cell else [])
        for cell in cells_to_highlight:
            if cell:
                grid_x, grid_y = cell
                if (grid_x, grid_y) not in self.tiles:  # Only highlight empty cells
                    painter.setPen(QPen(QColor(*HIGHLIGHT_COLOR), 3))
                    painter.setBrush(QColor(*HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA))
                    rect = QRect(grid_x * CELL_SIZE, grid_y * CELL_SIZE,
                               CELL_SIZE, CELL_SIZE)
                    painter.drawRect(rect)

        # Draw marquee selection rectangle (in screen coordinates)
        if self.marquee_selecting and self.marquee_start_pos and self.marquee_current_pos:
            painter.resetTransform()  # Draw in screen space
            painter.setPen(QPen(QColor(74, 144, 226), 2, Qt.DashLine))
            painter.setBrush(QColor(74, 144, 226, 40))

            x1 = min(self.marquee_start_pos.x(), self.marquee_current_pos.x())
            y1 = min(self.marquee_start_pos.y(), self.marquee_current_pos.y())
            x2 = max(self.marquee_start_pos.x(), self.marquee_current_pos.x())
            y2 = max(self.marquee_start_pos.y(), self.marquee_current_pos.y())

            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

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
        """Handle middle mouse button press for panning and left click for marquee selection"""
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.LeftButton:
            # Check if clicking on a tile or empty space
            widget_at_pos = self.childAt(event.pos())
            if widget_at_pos is None or not isinstance(widget_at_pos, GridTile):
                # Clicking on empty space - start marquee selection
                self.marquee_selecting = True
                self.marquee_start_pos = event.pos()
                self.marquee_current_pos = event.pos()
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning and marquee selection"""
        if self.middle_mouse_pressed and self.last_pan_pos:
            delta = event.pos() - self.last_pan_pos
            self.pan_offset_x += delta.x()
            self.pan_offset_y += delta.y()
            self.last_pan_pos = event.pos()

            # Update tile positions
            self.update_tile_positions()

            self.update()
            event.accept()
        elif self.marquee_selecting:
            # Update marquee rectangle
            self.marquee_current_pos = event.pos()
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle middle mouse button release and marquee selection completion"""
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.last_pan_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        elif event.button() == Qt.LeftButton and self.marquee_selecting:
            # Complete marquee selection
            if self.marquee_start_pos and self.marquee_current_pos:
                # Calculate marquee bounds in screen coordinates
                x1 = min(self.marquee_start_pos.x(), self.marquee_current_pos.x())
                y1 = min(self.marquee_start_pos.y(), self.marquee_current_pos.y())
                x2 = max(self.marquee_start_pos.x(), self.marquee_current_pos.x())
                y2 = max(self.marquee_start_pos.y(), self.marquee_current_pos.y())
                marquee_rect = QRect(x1, y1, x2 - x1, y2 - y1)

                # Check each tile if it intersects with marquee
                modifiers = QApplication.keyboardModifiers()
                if modifiers != Qt.ShiftModifier:
                    # Clear previous selection if not shift-clicking
                    if self.viewer:
                        self.viewer.clear_grid_selection()

                for grid_pos, tile in self.tiles.items():
                    # Get tile's screen position
                    tile_rect = tile.geometry()
                    if marquee_rect.intersects(tile_rect):
                        if self.viewer:
                            self.viewer.selected_grid_tiles.add(grid_pos)
                            tile.set_selected(True)

            # Clear marquee state
            self.marquee_selecting = False
            self.marquee_start_pos = None
            self.marquee_current_pos = None
            self.update()
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
        grid_x, grid_y = grid_pos

        # Check if this is a multi-image drag
        mime_text = event.mimeData().text()
        num_images = 1
        try:
            data = json.loads(mime_text)
            if isinstance(data, dict) and "multi" in data:
                num_images = len(data["multi"])
        except (json.JSONDecodeError, KeyError):
            pass

        # Check if all cells for multi-image placement are available
        all_cells_available = True
        if num_images > 1:
            for i in range(num_images):
                check_pos = (grid_x + i, grid_y)
                if not (0 <= grid_x + i < self.grid_columns and
                       0 <= grid_y < self.grid_rows and
                       check_pos not in self.tiles):
                    all_cells_available = False
                    break

        # Only highlight if cell is empty and within bounds (and all cells for multi-image)
        if (0 <= grid_x < self.grid_columns and
            0 <= grid_y < self.grid_rows and
            grid_pos not in self.tiles and
            all_cells_available):
            if num_images > 1:
                # Highlight all cells for multi-image placement
                self.highlight_cells = [(grid_x + i, grid_y) for i in range(num_images)]
                self.highlight_cell = None
            else:
                # Single image highlight
                self.highlight_cell = grid_pos
                self.highlight_cells = []
        else:
            self.highlight_cell = None
            self.highlight_cells = []

        self.update()  # Trigger repaint
        event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        self.highlight_cell = None
        self.highlight_cells = []
        self.update()
    
    def dropEvent(self, event):
        grid_pos = self.get_grid_position(event.position().toPoint())
        grid_x, grid_y = grid_pos

        mime_text = event.mimeData().text()

        # Check if it's a multi-image drop
        try:
            data = json.loads(mime_text)
            if isinstance(data, dict) and "multi" in data:
                # Multi-image drop - place them horizontally
                file_paths = data["multi"]

                # Verify all cells are available
                all_cells_available = True
                for i in range(len(file_paths)):
                    check_pos = (grid_x + i, grid_y)
                    if not (0 <= grid_x + i < self.grid_columns and
                           0 <= grid_y < self.grid_rows and
                           check_pos not in self.tiles):
                        all_cells_available = False
                        break

                if all_cells_available:
                    # Always create new tiles
                    for i, file_path in enumerate(file_paths):
                        current_grid_pos = (grid_x + i, grid_y)
                        tile = GridTile(file_path, self, self.viewer)
                        pixel_pos = self.get_pixel_position(current_grid_pos)
                        tile.move(pixel_pos)
                        tile.show()
                        self.tiles[current_grid_pos] = tile

                    event.acceptProposedAction()

                self.highlight_cell = None
                self.highlight_cells = []
                self.update()
                return
        except (json.JSONDecodeError, KeyError, TypeError):
            # Not a multi-image drop, continue with single-image handling
            pass

        # Only drop if cell is empty and within bounds
        if (0 <= grid_x < self.grid_columns and
            0 <= grid_y < self.grid_rows and
            grid_pos not in self.tiles):

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
                tile = GridTile(file_path, self, self.viewer)
                pixel_pos = self.get_pixel_position(grid_pos)
                tile.move(pixel_pos)
                tile.show()
                self.tiles[grid_pos] = tile
                event.acceptProposedAction()

        self.highlight_cell = None
        self.highlight_cells = []
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
            # Clear selection if needed
            if self.viewer and pos in self.viewer.selected_grid_tiles:
                self.viewer.selected_grid_tiles.remove(pos)
            self.tiles[pos].deleteLater()
            del self.tiles[pos]
        self.update()

    def cleanup_multi_drag(self):
        """Clean up tiles after multi-tile drag completes"""
        if self.dragged_tiles:
            # Delete tiles that weren't reused
            for tile in self.dragged_tiles.values():
                # Check if tile was reused (still in self.tiles)
                if tile not in self.tiles.values():
                    tile.deleteLater()
            self.dragged_tiles = None

    def set_grid_dimensions(self, rows, columns):
        """Update the grid dimensions"""
        self.grid_rows = rows
        self.grid_columns = columns
        # Remove tiles that are now outside the bounds
        positions_to_remove = [pos for pos in self.tiles.keys()
                              if pos[0] >= columns or pos[1] >= rows]
        for pos in positions_to_remove:
            self.tiles[pos].deleteLater()
            del self.tiles[pos]
        self.update()