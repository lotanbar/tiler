from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtGui import QDrag, QPainter, QFont
from PySide6.QtCore import Qt, QMimeData
from constants import DRAG_PREVIEW_SIZE, SELECTION_BORDER_COLOR, SELECTION_BORDER_WIDTH, scale_pixmap
import json

class ClickableLabel(QLabel):
    """Custom label that handles click events for selection and drag"""
    def __init__(self, file_path, parent_viewer):
        super().__init__()
        self.file_path = file_path
        self.parent_viewer = parent_viewer
        self.selected = False
        self.drag_start_position = None
        self.is_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = False
            modifiers = QApplication.keyboardModifiers()

            if modifiers == Qt.ShiftModifier:
                self.parent_viewer.select_range(self.file_path)
            # For plain click, we'll handle it in mouseReleaseEvent to distinguish from drag
        elif event.button() == Qt.RightButton:
            self.parent_viewer.show_large_image(self.file_path)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Mark that we're dragging
        self.is_dragging = True

        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()

        # Check if dragging multiple selected images
        if self.file_path in self.parent_viewer.selected_paths and len(self.parent_viewer.selected_paths) > 1:
            # Dragging multiple images - encode as JSON
            # Maintain order from image_paths (bank order) and include indices
            selected_data = []
            for idx, path in enumerate(self.parent_viewer.image_paths):
                if path in self.parent_viewer.selected_paths:
                    selected_data.append({
                        "path": path,
                        "bank_index": idx
                    })
            mime_data.setText(json.dumps({"multi": selected_data}))

            # Set drag preview with count indicator
            preview_pixmap = scale_pixmap(self.file_path, DRAG_PREVIEW_SIZE, keep_aspect=False)
            # Draw count badge on preview
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

            drag.setMimeData(mime_data)
            drag.setPixmap(preview_pixmap)
            drag.setHotSpot(preview_pixmap.rect().center())

            result = drag.exec(Qt.MoveAction)
            # If drop was successful, remove all selected images from bank
            if result == Qt.MoveAction:
                for item in selected_data:
                    self.parent_viewer.remove_from_bank(item["path"])
        else:
            # Dragging single image - include bank index
            bank_index = self.parent_viewer.image_paths.index(self.file_path)
            mime_data.setText(json.dumps({
                "path": self.file_path,
                "bank_index": bank_index
            }))
            drag.setMimeData(mime_data)

            # Set drag preview
            preview_pixmap = scale_pixmap(self.file_path, DRAG_PREVIEW_SIZE, keep_aspect=False)
            drag.setPixmap(preview_pixmap)
            drag.setHotSpot(preview_pixmap.rect().center())

            result = drag.exec(Qt.MoveAction)
            # If drop was successful, remove from bank
            if result == Qt.MoveAction:
                self.parent_viewer.remove_from_bank(self.file_path)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            # If plain click without drag and no modifiers
            if not self.is_dragging and modifiers == Qt.NoModifier:
                # Left click enters select mode and toggles selection
                if not self.parent_viewer.select_mode:
                    self.parent_viewer.toggle_select_mode()
                self.parent_viewer.toggle_selection(self.file_path)

    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.setStyleSheet(f"border: {SELECTION_BORDER_WIDTH}px solid {SELECTION_BORDER_COLOR};")
        else:
            self.setStyleSheet("")