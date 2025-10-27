from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QPushButton, QLabel, 
                               QFileDialog, QScrollArea, QHBoxLayout)
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
        
        # Import button
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        layout.addWidget(import_btn)
        
        # Scroll area for images at bottom
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)
        
        # Container for images (horizontal layout)
        self.image_container = QWidget()
        self.image_layout = QHBoxLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignLeft)
        scroll.setWidget(self.image_container)
        
        layout.addWidget(scroll)
        
    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if files:
            for file_path in files:
                self.add_image_thumbnail(file_path)
    
    def add_image_thumbnail(self, file_path):
        label = QLabel()
        pixmap = QPixmap(file_path)
        # Scale to thumbnail size (150px height)
        pixmap = pixmap.scaledToHeight(150, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        self.image_layout.addWidget(label)

app = QApplication(sys.argv)
window = ImageViewer()
window.show()
sys.exit(app.exec())