from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QPushButton, QLabel, 
                               QFileDialog, QScrollArea, QGridLayout, 
                               QDialog, QSplitter)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import sys
import os

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
        
        # Create splitter (allows resizing between top and bottom)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(20)  # Make handle thicker (default is ~3-4px)
        
        # Top section with button
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        top_layout.addWidget(import_btn)
        top_layout.addStretch()  # Push button to top
        
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
        
        # Set initial sizes (top: 80%, bottom: 20%)
        splitter.setSizes([480, 120])
        
        main_layout.addWidget(splitter)
        
        self.image_paths = []
        self.thumbnail_width = 120
        
    def import_images(self):
        # Get Desktop path
        desktop_path = os.path.expanduser("~/Desktop")
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            desktop_path,  # Start in Desktop directory
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if files:
            self.image_paths.extend(files)
            self.refresh_grid()
    
    def refresh_grid(self):
        # Clear existing grid
        for i in reversed(range(self.image_layout.count())):
            self.image_layout.itemAt(i).widget().setParent(None)
        
        # Calculate columns based on current width
        available_width = self.scroll.viewport().width()
        images_per_row = max(1, available_width // (self.thumbnail_width + 10))
        
        # Add all images to grid
        for index, file_path in enumerate(self.image_paths):
            label = QLabel()
            pixmap = QPixmap(file_path)
            pixmap = pixmap.scaledToWidth(self.thumbnail_width, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            
            # Make label clickable
            label.mousePressEvent = lambda event, path=file_path: self.show_large_image(path)
            label.setCursor(Qt.PointingHandCursor)
            
            # Calculate grid position
            row = index // images_per_row
            col = index % images_per_row
            
            self.image_layout.addWidget(label, row, col)
    
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