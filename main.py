from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QPushButton, QLabel, 
                               QFileDialog, QScrollArea, QGridLayout, 
                               QDialog, QSplitter, QHBoxLayout)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import sys
import os

class ClickableLabel(QLabel):
    """Custom label that handles click events for selection"""
    def __init__(self, file_path, parent_viewer):
        super().__init__()
        self.file_path = file_path
        self.parent_viewer = parent_viewer
        self.selected = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            
            if modifiers == Qt.ShiftModifier:
                # Shift: select range
                self.parent_viewer.select_range(self.file_path)
            elif modifiers == Qt.ControlModifier:
                # Ctrl: toggle individual selection
                self.parent_viewer.toggle_selection(self.file_path)
            else:
                # No modifier: select only this one
                self.parent_viewer.select_single(self.file_path)
        elif event.button() == Qt.RightButton:
            # Right click: show large image
            self.parent_viewer.show_large_image(self.file_path)
    
    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.setStyleSheet("border: 3px solid #4A90E2;")
        else:
            self.setStyleSheet("")

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Bank")
        self.setGeometry(100, 100, 800, 600)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(20)
        
        # Top section with buttons
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        button_row = QHBoxLayout()
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        button_row.addWidget(import_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setVisible(False)  # Hidden until selection
        button_row.addWidget(self.delete_btn)
        
        button_row.addStretch()
        top_layout.addLayout(button_row)
        top_layout.addStretch()
        
        # Bottom section with image grid
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        self.image_container = QWidget()
        self.image_layout = QGridLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.image_layout.setSpacing(5)
        self.scroll.setWidget(self.image_container)
        
        bottom_layout.addWidget(self.scroll)
        
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([480, 120])
        
        main_layout.addWidget(splitter)
        
        self.image_paths = []
        self.selected_paths = set()
        self.last_selected_index = None
        self.thumbnail_width = 100
        self.image_labels = {}  # Map file_path -> ClickableLabel
        
    def import_images(self):
        desktop_path = os.path.expanduser("~/Desktop")
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            desktop_path,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if files:
            self.image_paths.extend(files)
            self.refresh_grid()
    
    def select_single(self, file_path):
        """Select only this image, deselect all others"""
        self.clear_selection()
        self.selected_paths.add(file_path)
        self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
    
    def toggle_selection(self, file_path):
        """Toggle selection of this image (Ctrl+Click)"""
        if file_path in self.selected_paths:
            self.selected_paths.remove(file_path)
            self.image_labels[file_path].set_selected(False)
        else:
            self.selected_paths.add(file_path)
            self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
    
    def select_range(self, file_path):
        """Select range from last selected to this one (Shift+Click)"""
        if self.last_selected_index is None:
            self.select_single(file_path)
            return
        
        current_index = self.image_paths.index(file_path)
        start = min(self.last_selected_index, current_index)
        end = max(self.last_selected_index, current_index)
        
        for i in range(start, end + 1):
            path = self.image_paths[i]
            self.selected_paths.add(path)
            self.image_labels[path].set_selected(True)
        
        self.update_delete_button()
    
    def clear_selection(self):
        """Deselect all images"""
        for path in self.selected_paths:
            if path in self.image_labels:
                self.image_labels[path].set_selected(False)
        self.selected_paths.clear()
        self.update_delete_button()
    
    def update_delete_button(self):
        """Show/hide delete button based on selection"""
        self.delete_btn.setVisible(len(self.selected_paths) > 0)
    
    def delete_selected(self):
        """Remove selected images"""
        for path in self.selected_paths:
            if path in self.image_paths:
                self.image_paths.remove(path)
        
        self.selected_paths.clear()
        self.last_selected_index = None
        self.refresh_grid()
    
    def refresh_grid(self):
        # Clear existing grid
        for i in reversed(range(self.image_layout.count())):
            self.image_layout.itemAt(i).widget().setParent(None)
        
        self.image_labels.clear()
        
        # Calculate columns based on current width
        available_width = self.scroll.viewport().width()
        images_per_row = max(1, available_width // (self.thumbnail_width + 10))
        
        # Add all images to grid
        for index, file_path in enumerate(self.image_paths):
            label = ClickableLabel(file_path, self)
            pixmap = QPixmap(file_path)
            pixmap = pixmap.scaledToWidth(self.thumbnail_width, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setCursor(Qt.PointingHandCursor)
            
            # Restore selection state if it was selected
            if file_path in self.selected_paths:
                label.set_selected(True)
            
            self.image_labels[file_path] = label
            
            # Calculate grid position
            row = index // images_per_row
            col = index % images_per_row
            
            self.image_layout.addWidget(label, row, col)
        
        self.update_delete_button()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_paths:
            self.refresh_grid()
    
    def show_large_image(self, file_path):
        dialog = QDialog(self)
        dialog.setWindowTitle("View Image")
        layout = QVBoxLayout(dialog)
        
        label = QLabel()
        pixmap = QPixmap(file_path)
        pixmap = pixmap.scaledToWidth(800, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(label)
        dialog.exec()

app = QApplication(sys.argv)
window = ImageViewer()
window.show()
sys.exit(app.exec())