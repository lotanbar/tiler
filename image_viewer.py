from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton,
                               QLabel, QFileDialog, QScrollArea, QGridLayout,
                               QDialog, QSplitter, QHBoxLayout)
from PySide6.QtCore import Qt
import os

from grid_canvas import InfiniteGridCanvas
from image_bank import ClickableLabel
from constants import THUMBNAIL_WIDTH, LARGE_VIEW_WIDTH, scale_pixmap

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Bank")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(20)
        
        # Top section with infinite grid canvas
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Buttons
        button_row = QHBoxLayout()
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        button_row.addWidget(import_btn)
        
        clear_grid_btn = QPushButton("Clear Grid")
        clear_grid_btn.clicked.connect(self.clear_grid)
        button_row.addWidget(clear_grid_btn)
        
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setVisible(False)
        button_row.addWidget(self.delete_btn)
        
        button_row.addStretch()
        top_layout.addLayout(button_row)
        
        # Scrollable canvas for infinite grid
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(False)  # Don't auto-resize, we want scrollbars
        
        self.canvas = InfiniteGridCanvas()
        canvas_scroll.setWidget(self.canvas)
        top_layout.addWidget(canvas_scroll)
        
        # Bottom section with image bank
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        bank_label = QLabel("Image Bank (Drag images to grid above)")
        bank_label.setStyleSheet("padding: 5px; background-color: #e0e0e0; font-weight: bold;")
        bottom_layout.addWidget(bank_label)
        
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
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        self.image_paths = []
        self.selected_paths = set()
        self.last_selected_index = None
        self.image_labels = {}
        
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
    
    def clear_grid(self):
        """Clear all images from the canvas"""
        self.canvas.clear_all()
    
    def select_single(self, file_path):
        self.clear_selection()
        self.selected_paths.add(file_path)
        self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
    
    def toggle_selection(self, file_path):
        if file_path in self.selected_paths:
            self.selected_paths.remove(file_path)
            self.image_labels[file_path].set_selected(False)
        else:
            self.selected_paths.add(file_path)
            self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
    
    def select_range(self, file_path):
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
        for path in self.selected_paths:
            if path in self.image_labels:
                self.image_labels[path].set_selected(False)
        self.selected_paths.clear()
        self.update_delete_button()
    
    def update_delete_button(self):
        self.delete_btn.setVisible(len(self.selected_paths) > 0)
    
    def delete_selected(self):
        for path in list(self.selected_paths):
            if path in self.image_paths:
                self.image_paths.remove(path)
            # Remove tiles from canvas
            self.canvas.remove_tiles_by_path(path)

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
        images_per_row = max(1, available_width // (THUMBNAIL_WIDTH + 10))

        # Add all images to grid
        for index, file_path in enumerate(self.image_paths):
            label = ClickableLabel(file_path, self)
            pixmap = scale_pixmap(file_path, THUMBNAIL_WIDTH)
            label.setPixmap(pixmap)
            label.setCursor(Qt.PointingHandCursor)
            
            if file_path in self.selected_paths:
                label.set_selected(True)
            
            self.image_labels[file_path] = label
            
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
        pixmap = scale_pixmap(file_path, LARGE_VIEW_WIDTH)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)
        dialog.exec()