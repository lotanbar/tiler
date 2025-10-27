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

        pixmap = scale_pixmap(file_path, CELL_SIZE, keep_aspect=False)
        self.setPixmap(pixmap)
        self.setFixedSize(CELL_SIZE, CELL_SIZE)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: white;")
        
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

        # Remove this tile from canvas during drag
        self.parent_canvas.remove_tile_at_position(self.pos())
        
        if drag.exec(Qt.MoveAction) == Qt.IgnoreAction:
            # Drag cancelled, restore tile
            self.parent_canvas.add_tile_at_position(self, self.pos())

class InfiniteGridCanvas(QWidget):
    """Infinite grid canvas for placing images"""
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.highlight_cell = None  # Cell to highlight during drag
        self.tiles = {}  # Dictionary: (grid_x, grid_y) -> GridTile

        # Set minimum size for scrolling
        self.setMinimumSize(2000, 2000)
        
    def paintEvent(self, event):
        """Draw grid lines"""
        painter = QPainter(self)
        painter.setPen(QPen(QColor(*GRID_LINE_COLOR), 1))

        # Draw vertical lines
        for x in range(0, self.width(), CELL_SIZE):
            painter.drawLine(x, 0, x, self.height())

        # Draw horizontal lines
        for y in range(0, self.height(), CELL_SIZE):
            painter.drawLine(0, y, self.width(), y)

        # Highlight cell during drag
        if self.highlight_cell:
            grid_x, grid_y = self.highlight_cell
            if (grid_x, grid_y) not in self.tiles:  # Only highlight empty cells
                painter.setPen(QPen(QColor(*HIGHLIGHT_COLOR), 3))
                painter.setBrush(QColor(*HIGHLIGHT_COLOR, HIGHLIGHT_ALPHA))
                rect = QRect(grid_x * CELL_SIZE, grid_y * CELL_SIZE,
                           CELL_SIZE, CELL_SIZE)
                painter.drawRect(rect)
    
    def get_grid_position(self, pos):
        """Convert pixel position to grid coordinates"""
        grid_x = pos.x() // CELL_SIZE
        grid_y = pos.y() // CELL_SIZE
        return (grid_x, grid_y)

    def get_pixel_position(self, grid_pos):
        """Convert grid coordinates to pixel position"""
        grid_x, grid_y = grid_pos
        return QPoint(grid_x * CELL_SIZE, grid_y * CELL_SIZE)
    
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
                file_path = mime_text[5:]  # Remove "TILE:" prefix
            else:
                file_path = mime_text
            
            # Create new tile at this position
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