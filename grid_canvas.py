from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QDrag, QFont
from PySide6.QtCore import Qt, QMimeData, QPoint, QRect, QTimer
from constants import CELL_SIZE, GRID_LINE_COLOR, HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA, scale_pixmap, GRID_ROWS, GRID_COLUMNS, GRID_TILE_SELECTION_COLOR, SELECTION_BORDER_WIDTH, DRAG_PREVIEW_SIZE
import json
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tiler_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GridTile(QLabel):
    """Tile that can be placed on grid and moved"""
    # Class-level counter for tracking instances
    _instance_counter = 0

    def __init__(self, file_path, parent_canvas, viewer, original_bank_index=None):
        super().__init__(parent_canvas)
        GridTile._instance_counter += 1
        self._instance_id = GridTile._instance_counter
        logger.debug(f"[TILE-{self._instance_id}] Created for {file_path}, bank_index={original_bank_index}")

        self.file_path = file_path
        self.parent_canvas = parent_canvas
        self.viewer = viewer
        self.original_bank_index = original_bank_index  # Index in bank where this tile came from
        self.drag_start_position = None
        self.is_dragging = False
        self.selected = False
        self._is_deleted = False

        self.update_pixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: white;")

    def update_pixmap(self):
        """Update pixmap based on current zoom level"""
        if self._is_deleted:
            logger.error(f"[TILE-{self._instance_id}] ⚠️ update_pixmap called on DELETED tile!")
            return
        try:
            scaled_size = int(CELL_SIZE * self.parent_canvas.zoom_scale)
            pixmap = scale_pixmap(self.file_path, scaled_size, keep_aspect=False)
            if pixmap is None:
                logger.warning(f"[TILE-{self._instance_id}] Failed to load pixmap for {self.file_path}")
                return
            self.setPixmap(pixmap)
            self.setFixedSize(scaled_size, scaled_size)
        except Exception as e:
            logger.error(f"[TILE-{self._instance_id}] Exception in update_pixmap: {e}\n{traceback.format_exc()}")

    def deleteLater(self):
        """Override to track deletion"""
        logger.debug(f"[TILE-{self._instance_id}] deleteLater() called for {self.file_path}")
        logger.debug(f"[TILE-{self._instance_id}] Call stack:\n{traceback.format_stack()}")
        self._is_deleted = True
        super().deleteLater()

    def set_selected(self, selected):
        """Set selection state and update visual styling"""
        if self._is_deleted:
            logger.error(f"[TILE-{self._instance_id}] ⚠️ set_selected called on DELETED tile!")
            logger.error(f"Call stack:\n{''.join(traceback.format_stack())}")
            return
        try:
            self.selected = selected
            if selected:
                self.setStyleSheet(f"background-color: white; border: {SELECTION_BORDER_WIDTH}px solid {GRID_TILE_SELECTION_COLOR};")
            else:
                self.setStyleSheet("background-color: white;")
            logger.debug(f"[TILE-{self._instance_id}] set_selected({selected}) completed")
        except Exception as e:
            logger.error(f"[TILE-{self._instance_id}] Exception in set_selected: {e}\n{traceback.format_exc()}")

    def mousePressEvent(self, event):
        if self._is_deleted:
            logger.error(f"[TILE-{self._instance_id}] ⚠️ mousePressEvent called on DELETED tile!")
            return
        try:
            if event.button() == Qt.LeftButton:
                self.drag_start_position = event.pos()
                self.is_dragging = False
                self.raise_()  # Bring to front
            elif event.button() == Qt.RightButton:
                self.viewer.show_large_image(self.file_path)
        except Exception as e:
            logger.error(f"[TILE-{self._instance_id}] Exception in mousePressEvent: {e}\n{traceback.format_exc()}")
    
    def mouseMoveEvent(self, event):
        if self._is_deleted:
            logger.error(f"[TILE-{self._instance_id}] ⚠️ mouseMoveEvent called on DELETED tile!")
            return
        try:
            if not (event.buttons() & Qt.LeftButton):
                return
            if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                return

            # Mark that we're dragging
            self.is_dragging = True
        except Exception as e:
            logger.error(f"[TILE-{self._instance_id}] Exception in mouseMoveEvent start: {e}\n{traceback.format_exc()}")
            return

        # Get grid position of this tile
        grid_pos = self.parent_canvas.get_grid_position(self.pos())

        # Check if dragging multiple selected tiles
        if (self.viewer and
            grid_pos in self.viewer.selected_grid_tiles and
            len(self.viewer.selected_grid_tiles) > 1):

            logger.info(f"[TILE-{self._instance_id}] Starting multi-tile drag of {len(self.viewer.selected_grid_tiles)} tiles")

            # Multi-tile drag - get all selected tiles sorted by position (row, col)
            selected_positions = sorted(list(self.viewer.selected_grid_tiles),
                                       key=lambda p: (p[1], p[0]))  # Sort by row, then column

            # Collect both file paths and original bank indices
            selected_data = []
            for pos in selected_positions:
                tile = self.parent_canvas.tiles[pos]
                logger.debug(f"[TILE-{tile._instance_id}] Added to multi-drag at pos {pos}")
                selected_data.append({
                    "path": tile.file_path,
                    "bank_index": tile.original_bank_index
                })

            # Start drag operation
            # IMPORTANT: Use parent_canvas as parent, not self (tile)
            # If we use self, Qt crashes when accessing the hidden tile after drag
            drag = QDrag(self.parent_canvas)
            mime_data = QMimeData()
            mime_data.setText(json.dumps({"multi": selected_data}))
            drag.setMimeData(mime_data)
            logger.debug(f"[TILE-{self._instance_id}] Created QDrag with canvas as parent (not tile)")

            # Set drag preview with count indicator
            preview_pixmap = scale_pixmap(self.file_path, DRAG_PREVIEW_SIZE, keep_aspect=False)
            if preview_pixmap is None:
                logger.error(f"[TILE-{self._instance_id}] Failed to create preview pixmap, aborting drag")
                return

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
                           Qt.AlignCenter, str(len(selected_data)))
            painter.end()

            drag.setPixmap(preview_pixmap)
            drag.setHotSpot(preview_pixmap.rect().center())

            # Store tiles and remove all selected tiles during drag
            self.parent_canvas.dragged_tiles = {}  # Map: grid_pos -> tile
            for pos in selected_positions:
                tile = self.parent_canvas.tiles[pos]
                logger.debug(f"[TILE-{tile._instance_id}] Removed from grid at pos {pos} for drag")
                self.parent_canvas.dragged_tiles[pos] = tile
                tile.hide()  # Hide tiles during drag for better UX
                del self.parent_canvas.tiles[pos]

            logger.debug("Starting drag.exec() - this blocks until drag completes")
            result = drag.exec(Qt.MoveAction)
            logger.debug(f"drag.exec() returned - now sleeping 150ms for Qt cleanup")
            # CRITICAL: Sleep to allow Qt's internal drag cleanup to complete
            # Without this, Qt crashes when accessing hidden tiles
            import time
            time.sleep(0.15)  # 150ms delay
            logger.debug("Sleep complete - safe to proceed")
            logger.info(f"[TILE-{self._instance_id}] Multi-drag result: {result}")

            # If drag cancelled, restore all tiles
            if result == Qt.IgnoreAction:
                logger.info(f"Multi-drag cancelled - restoring {len(self.parent_canvas.dragged_tiles)} tiles")
                for pos, tile in self.parent_canvas.dragged_tiles.items():
                    logger.debug(f"[TILE-{tile._instance_id}] Restored to pos {pos}")
                    self.parent_canvas.tiles[pos] = tile
                    tile.show()
                self.parent_canvas.dragged_tiles = None

                # Clear selection even on cancelled drag
                if self.viewer:
                    logger.debug("Clearing selection after cancelled drag")
                    self.viewer.clear_grid_selection()
            elif result == Qt.MoveAction:
                # Drop succeeded
                logger.info(f"Multi-drag succeeded - {len(self.parent_canvas.dragged_tiles)} tiles were dragged")
                # Clear selection first
                if self.viewer:
                    logger.debug("ABOUT TO CALL clear_grid_selection()")
                    self.viewer.clear_grid_selection()
                    logger.debug("clear_grid_selection() RETURNED SUCCESSFULLY")

                # DON'T delete tiles from here - let the canvas handle cleanup
                # Schedule cleanup with delay to allow Qt's internal cleanup to finish
                # Using 100ms delay to ensure all drag-related events are processed
                logger.debug("Scheduling cleanup_multi_drag() with 100ms delay")
                QTimer.singleShot(100, self.parent_canvas.cleanup_multi_drag)
                logger.debug("mouseMoveEvent multi-drag ABOUT TO RETURN")

        else:
            # Single tile drag
            drag = QDrag(self)
            mime_data = QMimeData()
            # Include bank index in single tile drag too
            tile_data = {
                "path": self.file_path,
                "bank_index": self.original_bank_index
            }
            mime_data.setText(f"TILE:{json.dumps(tile_data)}")
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
        self.setFocusPolicy(Qt.StrongFocus)  # Enable keyboard focus
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
        self.ctrl_left_mouse_pressed = False  # Track Ctrl+Left mouse panning
        self.last_pan_pos = None

        # Keyboard control settings
        self.PAN_STEP = 50  # Pixels to pan per arrow key press
        self.KEYBOARD_ZOOM_FACTOR = 1.1  # Zoom factor for keyboard zoom

        # Marquee selection state
        self.marquee_selecting = False
        self.marquee_start_pos = None
        self.marquee_current_pos = None
        
    def paintEvent(self, event):
        """Draw grid lines with zoom and pan transformations"""
        logger.debug("paintEvent START")
        try:
            painter = QPainter(self)
        except Exception as e:
            logger.error(f"Exception creating QPainter: {e}\n{traceback.format_exc()}")
            return

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

        logger.debug("paintEvent END")

    def wheelEvent(self, event):
        """Handle zoom with scroll wheel"""
        logger.debug("wheelEvent START")
        try:
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

            logger.debug(f"wheelEvent calling update_tile_positions() - {len(self.tiles)} tiles")
            # Update tile positions
            self.update_tile_positions()
            logger.debug("wheelEvent update_tile_positions() completed")

            self.update()
            event.accept()
            logger.debug("wheelEvent END")
        except Exception as e:
            logger.error(f"Exception in wheelEvent: {e}\n{traceback.format_exc()}")

    def mousePressEvent(self, event):
        """Handle middle mouse button press for panning and left click for marquee selection"""
        # Grab focus when clicked
        self.setFocus()

        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()

            # Ctrl+Left Click to start drag-to-pan (like middle mouse)
            if modifiers == Qt.ControlModifier:
                self.ctrl_left_mouse_pressed = True
                self.last_pan_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
            else:
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
        if (self.middle_mouse_pressed or self.ctrl_left_mouse_pressed) and self.last_pan_pos:
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
        elif event.button() == Qt.LeftButton and self.ctrl_left_mouse_pressed:
            # Release Ctrl+Left drag panning
            self.ctrl_left_mouse_pressed = False
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

    def keyPressEvent(self, event):
        """Handle keyboard input for panning and zooming"""
        key = event.key()
        modifiers = event.modifiers()

        # Arrow keys for panning
        if key == Qt.Key_Left:
            self.pan_offset_x += self.PAN_STEP
            self.update_tile_positions()
            self.update()
            event.accept()
        elif key == Qt.Key_Right:
            self.pan_offset_x -= self.PAN_STEP
            self.update_tile_positions()
            self.update()
            event.accept()
        elif key == Qt.Key_Up:
            self.pan_offset_y += self.PAN_STEP
            self.update_tile_positions()
            self.update()
            event.accept()
        elif key == Qt.Key_Down:
            self.pan_offset_y -= self.PAN_STEP
            self.update_tile_positions()
            self.update()
            event.accept()

        # Ctrl+Plus/Minus for zooming
        elif modifiers == Qt.ControlModifier and (key == Qt.Key_Plus or key == Qt.Key_Equal):
            # Zoom in
            self.zoom_in_keyboard()
            event.accept()
        elif modifiers == Qt.ControlModifier and (key == Qt.Key_Minus or key == Qt.Key_Underscore):
            # Zoom out
            self.zoom_out_keyboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    def zoom_in_keyboard(self):
        """Zoom in using keyboard (zooms toward center of viewport)"""
        # Calculate new zoom level
        new_zoom = self.zoom_scale * self.KEYBOARD_ZOOM_FACTOR

        # Apply zoom limits
        if new_zoom > self.MAX_ZOOM:
            new_zoom = self.MAX_ZOOM

        # Store old zoom for position adjustment
        old_zoom = self.zoom_scale
        self.zoom_scale = new_zoom

        # Zoom toward center of viewport
        center_x = self.width() / 2
        center_y = self.height() / 2
        self.pan_offset_x = center_x - (center_x - self.pan_offset_x) * (new_zoom / old_zoom)
        self.pan_offset_y = center_y - (center_y - self.pan_offset_y) * (new_zoom / old_zoom)

        # Update tile positions
        self.update_tile_positions()
        self.update()

    def zoom_out_keyboard(self):
        """Zoom out using keyboard (zooms toward center of viewport)"""
        # Calculate new zoom level
        new_zoom = self.zoom_scale / self.KEYBOARD_ZOOM_FACTOR

        # Apply zoom limits
        if new_zoom < self.MIN_ZOOM:
            new_zoom = self.MIN_ZOOM

        # Store old zoom for position adjustment
        old_zoom = self.zoom_scale
        self.zoom_scale = new_zoom

        # Zoom toward center of viewport
        center_x = self.width() / 2
        center_y = self.height() / 2
        self.pan_offset_x = center_x - (center_x - self.pan_offset_x) * (new_zoom / old_zoom)
        self.pan_offset_y = center_y - (center_y - self.pan_offset_y) * (new_zoom / old_zoom)

        # Update tile positions
        self.update_tile_positions()
        self.update()

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
        logger.debug(f"update_tile_positions START - {len(self.tiles)} tiles to update")
        try:
            tile_list = list(self.tiles.items())  # Use list() to avoid dict change during iteration
            logger.debug(f"Created tile list snapshot with {len(tile_list)} items")

            for idx, (grid_pos, tile) in enumerate(tile_list):
                try:
                    tile_id = tile._instance_id if hasattr(tile, '_instance_id') else 'UNKNOWN'
                    logger.debug(f"[{idx+1}/{len(tile_list)}] Updating TILE-{tile_id} at {grid_pos}")

                    if hasattr(tile, '_is_deleted') and tile._is_deleted:
                        logger.error(f"⚠️ DELETED TILE-{tile_id} still in self.tiles at {grid_pos}!")
                        logger.error(f"Call stack:\n{''.join(traceback.format_stack())}")
                        continue

                    logger.debug(f"[TILE-{tile_id}] Getting pixel position...")
                    pixel_pos = self.get_pixel_position(grid_pos)

                    logger.debug(f"[TILE-{tile_id}] Moving to {pixel_pos}...")
                    tile.move(pixel_pos)

                    logger.debug(f"[TILE-{tile_id}] Updating pixmap...")
                    # Update tile pixmap and size based on zoom
                    tile.update_pixmap()

                    logger.debug(f"[TILE-{tile_id}] Update complete")
                except RuntimeError as e:
                    logger.error(f"RuntimeError accessing tile at {grid_pos}: {e}\n{traceback.format_exc()}")
                except Exception as e:
                    logger.error(f"Exception updating tile at {grid_pos}: {e}\n{traceback.format_exc()}")

            logger.debug("update_tile_positions END - all tiles updated")
        except Exception as e:
            logger.error(f"Exception in update_tile_positions: {e}\n{traceback.format_exc()}")
    

    def validate_multi_drop_positions(self, grid_x, grid_y, num_images):
        """
        Validate that all positions for multi-image drop are available
        
        Args:
            grid_x: Starting grid X position
            grid_y: Grid Y position
            num_images: Number of images to place
            
        Returns:
            True if all positions are valid and available
        """
        for i in range(num_images):
            check_pos = (grid_x + i, grid_y)
            # Check bounds
            if grid_x + i >= self.grid_columns or grid_y >= self.grid_rows:
                return False
            # Check if cell is occupied
            if check_pos in self.tiles:
                return False
        return True
    
    
    def validate_multi_drop_positions(self, grid_x, grid_y, num_images):
        """
        Validate that all positions for multi-image drop are available
        
        Args:
            grid_x: Starting grid X position
            grid_y: Grid Y position
            num_images: Number of images to place
            
        Returns:
            True if all positions are valid and available
        """
        for i in range(num_images):
            check_pos = (grid_x + i, grid_y)
            # Check bounds
            if grid_x + i >= self.grid_columns or grid_y >= self.grid_rows:
                return False
            # Check if cell is occupied
            if check_pos in self.tiles:
                return False
        return True

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
        all_cells_available = self.validate_multi_drop_positions(grid_x, grid_y, num_images) if num_images > 1 else True

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
                multi_data = data["multi"]
                logger.info(f"Multi-image drop at ({grid_x}, {grid_y}) - {len(multi_data)} items")

                # Parse data - support both old format (list of strings) and new format (list of dicts)
                if multi_data and isinstance(multi_data[0], dict):
                    # New format with bank indices
                    items = multi_data
                else:
                    # Old format - just file paths (from bank)
                    items = [{"path": p, "bank_index": None} for p in multi_data]

                # Verify all cells are available
                if self.validate_multi_drop_positions(grid_x, grid_y, len(items)):
                    # Check if we're reusing dragged tiles
                    if self.dragged_tiles:
                        logger.info(f"REUSING {len(self.dragged_tiles)} existing tiles for multi-drop")
                        # Reuse existing tiles - just move them
                        for i, item in enumerate(items):
                            current_grid_pos = (grid_x + i, grid_y)
                            # Find matching tile from dragged_tiles by file path
                            matching_tile = None
                            for old_pos, tile in self.dragged_tiles.items():
                                if tile.file_path == item["path"]:
                                    matching_tile = tile
                                    break

                            if matching_tile:
                                logger.debug(f"[TILE-{matching_tile._instance_id}] Reusing tile at {current_grid_pos}")
                                pixel_pos = self.get_pixel_position(current_grid_pos)
                                matching_tile.move(pixel_pos)
                                matching_tile.show()
                                self.tiles[current_grid_pos] = matching_tile
                            else:
                                # Fallback: create new tile if no match found
                                logger.warning(f"No matching tile found for {item['path']}, creating new")
                                file_path = item["path"]
                                bank_index = item.get("bank_index")
                                tile = GridTile(file_path, self, self.viewer, bank_index)
                                pixel_pos = self.get_pixel_position(current_grid_pos)
                                tile.move(pixel_pos)
                                tile.show()
                                self.tiles[current_grid_pos] = tile
                    else:
                        logger.info(f"Creating {len(items)} NEW tiles for multi-drop (from bank)")
                        # New tiles from bank
                        for i, item in enumerate(items):
                            current_grid_pos = (grid_x + i, grid_y)
                            file_path = item["path"]
                            bank_index = item.get("bank_index")
                            tile = GridTile(file_path, self, self.viewer, bank_index)
                            logger.debug(f"[TILE-{tile._instance_id}] Created and placed at {current_grid_pos}")
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
                # New image from bank - parse JSON
                try:
                    data = json.loads(mime_text)
                    file_path = data.get("path", mime_text)  # Fallback to plain text
                    bank_index = data.get("bank_index")
                except (json.JSONDecodeError, AttributeError):
                    # Old format - plain file path
                    file_path = mime_text
                    bank_index = None

                tile = GridTile(file_path, self, self.viewer, bank_index)
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

    def add_tile_from_data(self, grid_pos, file_path, original_bank_index):
        """
        Add a tile to the grid from saved project data

        Args:
            grid_pos: Tuple (grid_x, grid_y) for tile position
            file_path: Path to the image file
            original_bank_index: Index in the bank where this tile originated
        """
        # Create new GridTile
        tile = GridTile(file_path, self, self.viewer, original_bank_index)

        # Add to tiles dictionary
        self.tiles[grid_pos] = tile

        # Position the tile correctly
        pixel_pos = self.get_pixel_position(grid_pos)
        tile.move(pixel_pos)
        tile.show()

        # Update the tile's visual state based on zoom
        tile.update_pixmap()

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
        logger.info(f"cleanup_multi_drag() STARTING - dragged_tiles: {self.dragged_tiles is not None}")
        if self.dragged_tiles:
            # Check if any tiles in dragged_tiles were NOT reused
            unused_tiles = []
            for pos, tile in self.dragged_tiles.items():
                if tile not in self.tiles.values():
                    unused_tiles.append((pos, tile))

            if unused_tiles:
                logger.info(f"Deleting {len(unused_tiles)} unused tiles")
                for pos, tile in unused_tiles:
                    logger.debug(f"[TILE-{tile._instance_id}] Deleting unused tile from pos {pos}")
                    tile.deleteLater()
            else:
                logger.info("All dragged tiles were reused - nothing to delete")

            self.dragged_tiles = None
            logger.info("Cleanup complete")
        else:
            logger.warning("cleanup_multi_drag() called but dragged_tiles is None")

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