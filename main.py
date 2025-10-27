from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QPushButton, QLabel, 
                               QFileDialog, QScrollArea, QGridLayout, QDialog)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import sys

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Bank")
        self.setGeometry(100, 100, 800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Import button
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        layout.addWidget(import_btn)
        
        # Scroll area for images at bottom
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        # Container for images (grid layout)
        self.image_container = QWidget()
        self.image_layout = QGridLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Center horizontally, top align
        self.image_layout.setSpacing(5)  # Reduce spacing between images
        self.scroll.setWidget(self.image_container)
        
        layout.addWidget(self.scroll)
        
        self.image_paths = []  # Store all image paths
        self.thumbnail_width = 150  # Thumbnail width in pixels
        
    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
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
        # Called whenever window is resized
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