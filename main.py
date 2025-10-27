from PySide6.QtWidgets import QApplication, QMainWindow
import sys

# Create the applicatoin
app = QApplication(sys.argv)

# Create the main window
window = QMainWindow()
window.setWindowTitle("My First Window")
window.setGeometry(100, 100, 400, 300)

# Show window
window.show()

# Run event loop 
sys.exit(app.exec())
