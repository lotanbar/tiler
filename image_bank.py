from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtGui import QDrag
from PySide6.QtCore import Qt, QMimeData
from constants import DRAG_PREVIEW_SIZE, SELECTION_BORDER_COLOR, SELECTION_BORDER_WIDTH, scale_pixmap

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
        mime_data.setText(self.file_path)
        drag.setMimeData(mime_data)

        # Set drag preview
        preview_pixmap = scale_pixmap(self.file_path, DRAG_PREVIEW_SIZE, keep_aspect=False)
        drag.setPixmap(preview_pixmap)
        drag.setHotSpot(preview_pixmap.rect().center())

        drag.exec(Qt.CopyAction)

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