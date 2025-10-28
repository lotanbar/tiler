from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton,
                               QLabel, QFileDialog, QScrollArea, QGridLayout,
                               QDialog, QSplitter, QHBoxLayout, QSpinBox, QApplication, QMessageBox, QMenu)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QAction, QKeySequence
import os

from grid_canvas import InfiniteGridCanvas
from image_bank import ClickableLabel
from constants import THUMBNAIL_WIDTH, LARGE_VIEW_WIDTH, scale_pixmap, GRID_ROWS, GRID_COLUMNS
from project_manager import ProjectManager

class ImageBankContainer(QWidget):
    """Container widget for image bank that accepts drops"""
    def __init__(self, parent_viewer):
        super().__init__()
        self.parent_viewer = parent_viewer
        self.setAcceptDrops(True)

        # Marquee selection state
        self.marquee_selecting = False
        self.marquee_start_pos = None
        self.marquee_current_pos = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            mime_text = event.mimeData().text()
            # Accept tiles being moved from grid (single or multi)
            if mime_text.startswith("TILE:"):
                event.acceptProposedAction()
            else:
                # Check for multi-tile JSON
                try:
                    import json
                    data = json.loads(mime_text)
                    if isinstance(data, dict) and "multi" in data:
                        event.acceptProposedAction()
                    else:
                        event.ignore()
                except (json.JSONDecodeError, KeyError, TypeError):
                    event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            mime_text = event.mimeData().text()
            if mime_text.startswith("TILE:"):
                event.acceptProposedAction()
            else:
                # Check for multi-tile JSON
                try:
                    import json
                    data = json.loads(mime_text)
                    if isinstance(data, dict) and "multi" in data:
                        event.acceptProposedAction()
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

    def dropEvent(self, event):
        mime_text = event.mimeData().text()

        # Check if it's a multi-tile drop from grid
        try:
            import json
            data = json.loads(mime_text)
            if isinstance(data, dict) and "multi" in data:
                # Multi-tile drop - add all back to bank
                multi_data = data["multi"]

                # Parse data - support both old format (list of strings) and new format (list of dicts)
                if multi_data and isinstance(multi_data[0], dict):
                    # New format with bank indices - restore to original positions
                    for item in multi_data:
                        file_path = item["path"]
                        bank_index = item.get("bank_index")
                        if bank_index is not None and 0 <= bank_index <= len(self.parent_viewer.image_paths):
                            # Insert at original position
                            if file_path not in self.parent_viewer.image_paths:
                                self.parent_viewer.image_paths.insert(bank_index, file_path)
                        else:
                            # No valid index, append to end
                            self.parent_viewer.add_to_bank(file_path)
                    self.parent_viewer.refresh_grid()
                else:
                    # Old format - just file paths, append to end
                    for file_path in multi_data:
                        self.parent_viewer.add_to_bank(file_path)

                event.acceptProposedAction()
                return
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Single tile drop
        if mime_text.startswith("TILE:"):
            tile_data_str = mime_text[5:]  # Remove "TILE:" prefix
            # Delete the dragged tile widget from the canvas
            if self.parent_viewer.canvas.dragged_tile:
                self.parent_viewer.canvas.dragged_tile.deleteLater()
                self.parent_viewer.canvas.dragged_tile = None

            # Parse tile data
            try:
                tile_data = json.loads(tile_data_str)
                file_path = tile_data["path"]
                bank_index = tile_data.get("bank_index")

                # Restore to original position if available
                if bank_index is not None and 0 <= bank_index <= len(self.parent_viewer.image_paths):
                    if file_path not in self.parent_viewer.image_paths:
                        self.parent_viewer.image_paths.insert(bank_index, file_path)
                    self.parent_viewer.refresh_grid()
                else:
                    # No valid index, append to end
                    self.parent_viewer.add_to_bank(file_path)
            except (json.JSONDecodeError, KeyError):
                # Old format - plain file path
                self.parent_viewer.add_to_bank(tile_data_str)

            event.acceptProposedAction()

    def paintEvent(self, event):
        """Draw marquee selection rectangle"""
        super().paintEvent(event)

        if self.marquee_selecting and self.marquee_start_pos and self.marquee_current_pos:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(74, 144, 226), 2, Qt.DashLine))
            painter.setBrush(QColor(74, 144, 226, 40))

            x1 = min(self.marquee_start_pos.x(), self.marquee_current_pos.x())
            y1 = min(self.marquee_start_pos.y(), self.marquee_current_pos.y())
            x2 = max(self.marquee_start_pos.x(), self.marquee_current_pos.x())
            y2 = max(self.marquee_start_pos.y(), self.marquee_current_pos.y())

            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def mousePressEvent(self, event):
        """Handle left click for marquee selection"""
        if event.button() == Qt.LeftButton:
            # Check if clicking on an image label or empty space
            widget_at_pos = self.childAt(event.pos())
            if widget_at_pos is None or not isinstance(widget_at_pos, ClickableLabel):
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
        """Handle mouse move for marquee selection"""
        if self.marquee_selecting:
            # Update marquee rectangle
            self.marquee_current_pos = event.pos()
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle marquee selection completion"""
        if event.button() == Qt.LeftButton and self.marquee_selecting:
            # Complete marquee selection
            if self.marquee_start_pos and self.marquee_current_pos:
                # Calculate marquee bounds
                x1 = min(self.marquee_start_pos.x(), self.marquee_current_pos.x())
                y1 = min(self.marquee_start_pos.y(), self.marquee_current_pos.y())
                x2 = max(self.marquee_start_pos.x(), self.marquee_current_pos.x())
                y2 = max(self.marquee_start_pos.y(), self.marquee_current_pos.y())
                marquee_rect = QRect(x1, y1, x2 - x1, y2 - y1)

                # Check modifiers
                modifiers = QApplication.keyboardModifiers()
                if modifiers != Qt.ShiftModifier:
                    # Clear previous selection if not shift-clicking
                    self.parent_viewer.clear_selection()

                # Enter select mode if not already
                if not self.parent_viewer.select_mode:
                    self.parent_viewer.toggle_select_mode()

                # Check each image label if it intersects with marquee
                for file_path, label in self.parent_viewer.image_labels.items():
                    # Get label's position in container coordinates
                    label_rect = label.geometry()
                    if marquee_rect.intersects(label_rect):
                        if file_path not in self.parent_viewer.selected_paths:
                            self.parent_viewer.selected_paths.add(file_path)
                            label.set_selected(True)
                            self.parent_viewer.last_selected_index = self.parent_viewer.image_paths.index(file_path)

                self.parent_viewer.update_delete_button()
                self.parent_viewer.update_select_all_button()

            # Clear marquee state
            self.marquee_selecting = False
            self.marquee_start_pos = None
            self.marquee_current_pos = None
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Bank")
        self.setGeometry(100, 100, 1200, 800)

        # Track current project file
        self.current_project_file = None

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

        # Infinite grid canvas (no scroll bars - use middle mouse to pan)
        self.canvas = InfiniteGridCanvas(viewer=self)
        top_layout.addWidget(self.canvas)
        
        # Bottom section with image bank
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        bank_label = QLabel("Image Bank (Drag images to/from grid above)")
        bank_label.setStyleSheet("padding: 5px; background-color: #e0e0e0; font-weight: bold;")
        bottom_layout.addWidget(bank_label)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.image_container = ImageBankContainer(self)
        self.image_layout = QGridLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.image_layout.setSpacing(5)
        self.scroll.setWidget(self.image_container)

        bottom_layout.addWidget(self.scroll)

        # Buttons at the bottom
        button_row = QHBoxLayout()

        # File menu button on the left
        file_menu_btn = QPushButton("File")
        file_menu = QMenu(self)

        # New Project action
        new_action = QAction("New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        # Save action
        save_action = QAction("Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("Save Project As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Load action
        load_action = QAction("Open Project...", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)

        file_menu_btn.setMenu(file_menu)
        button_row.addWidget(file_menu_btn)

        # Left side buttons
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        button_row.addWidget(import_btn)

        clear_grid_btn = QPushButton("Clear Grid")
        clear_grid_btn.clicked.connect(self.clear_grid)
        button_row.addWidget(clear_grid_btn)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        self.select_all_btn.setVisible(False)  # Hidden until select mode is on
        button_row.addWidget(self.select_all_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setVisible(False)
        button_row.addWidget(self.delete_btn)

        button_row.addStretch()

        # Grid controls on the right
        button_row.addWidget(QLabel("Grid Size:"))
        button_row.addWidget(QLabel("Rows:"))
        self.rows_input = QSpinBox()
        self.rows_input.setMinimum(1)
        self.rows_input.setMaximum(100)
        self.rows_input.setValue(GRID_ROWS)
        self.rows_input.setFixedWidth(60)
        button_row.addWidget(self.rows_input)

        button_row.addWidget(QLabel("Columns:"))
        self.columns_input = QSpinBox()
        self.columns_input.setMinimum(1)
        self.columns_input.setMaximum(100)
        self.columns_input.setValue(GRID_COLUMNS)
        self.columns_input.setFixedWidth(60)
        button_row.addWidget(self.columns_input)

        self.adjust_grid_btn = QPushButton("Adjust Grid")
        self.adjust_grid_btn.clicked.connect(self.adjust_grid_size)
        button_row.addWidget(self.adjust_grid_btn)

        bottom_layout.addLayout(button_row)

        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        self.image_paths = []
        self.selected_paths = set()
        self.last_selected_index = None
        self.image_labels = {}
        self.select_mode = False

        # Grid tile selection tracking
        self.selected_grid_tiles = set()  # Set of grid positions (grid_x, grid_y)
        self.last_selected_grid_pos = None  # For range selection

        # Development: Auto-load images from assets folder if it exists
        self.auto_load_assets()

    def new_project(self):
        """Create a new project (clear current state)"""
        reply = QMessageBox.question(
            self,
            "New Project",
            "Are you sure you want to start a new project? All unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Clear everything
            self.clear_grid()
            self.image_paths.clear()
            self.selected_paths.clear()
            self.last_selected_index = None
            self.current_project_file = None
            self.refresh_grid()
            self.setWindowTitle("Image Bank - New Project")

    def save_project(self):
        """Save the current project"""
        if self.current_project_file:
            # Save to existing file
            success = ProjectManager.save_project(
                self.current_project_file,
                self.canvas,
                self
            )
            if success:
                QMessageBox.information(self, "Success", "Project saved successfully!")
                self.setWindowTitle(f"Image Bank - {os.path.basename(self.current_project_file)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to save project!")
        else:
            # No file yet, do Save As
            self.save_project_as()

    def save_project_as(self):
        """Save the current project with a new filename"""
        desktop_path = os.path.expanduser("~/Desktop")

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            desktop_path,
            f"Tiler Projects (*{ProjectManager.DEFAULT_EXTENSION})"
        )

        if filepath:
            success = ProjectManager.save_project(filepath, self.canvas, self)
            if success:
                self.current_project_file = filepath
                QMessageBox.information(self, "Success", "Project saved successfully!")
                self.setWindowTitle(f"Image Bank - {os.path.basename(filepath)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to save project!")

    def load_project(self):
        """Load a project from a file"""
        desktop_path = os.path.expanduser("~/Desktop")

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            desktop_path,
            f"Tiler Projects (*{ProjectManager.DEFAULT_EXTENSION})"
        )

        if filepath:
            project_data = ProjectManager.load_project(filepath)

            if project_data is None:
                QMessageBox.warning(self, "Error", "Failed to load project! Check console for details.")
                return

            # Clear current state
            self.clear_grid()
            self.image_paths.clear()
            self.selected_paths.clear()

            # Load bank images
            self.image_paths = project_data["bank"]["image_paths"]
            self.refresh_grid()

            # Load grid settings
            grid_data = project_data["grid"]
            self.canvas.grid_rows = grid_data["rows"]
            self.canvas.grid_columns = grid_data["columns"]
            self.canvas.zoom_scale = grid_data["zoom_scale"]
            self.canvas.pan_offset_x = grid_data["pan_offset_x"]
            self.canvas.pan_offset_y = grid_data["pan_offset_y"]

            # Update UI controls
            self.rows_input.setValue(grid_data["rows"])
            self.columns_input.setValue(grid_data["columns"])

            # Load tiles
            for tile_data in project_data["tiles"]:
                grid_pos = (tile_data["grid_x"], tile_data["grid_y"])
                file_path = tile_data["file_path"]
                bank_index = tile_data["original_bank_index"]

                # Create tile on canvas
                self.canvas.add_tile_from_data(
                    grid_pos,
                    file_path,
                    bank_index
                )

            # Restore UI state if available
            if "ui_state" in project_data:
                ui_state = project_data["ui_state"]

                # Restore grid tile selections
                if "selected_grid_positions" in ui_state:
                    for pos_list in ui_state["selected_grid_positions"]:
                        grid_pos = tuple(pos_list)
                        if grid_pos in self.canvas.tiles:
                            self.selected_grid_tiles.add(grid_pos)
                            self.canvas.tiles[grid_pos].set_selected(True)

                # Restore bank selections
                if "selected_bank_paths" in ui_state:
                    for path in ui_state["selected_bank_paths"]:
                        if path in self.image_paths:
                            self.selected_paths.add(path)
                            if path in self.image_labels:
                                self.image_labels[path].set_selected(True)

            # Update canvas
            self.canvas.update()

            # Track current file
            self.current_project_file = filepath
            self.setWindowTitle(f"Image Bank - {os.path.basename(filepath)}")

            QMessageBox.information(self, "Success", "Project loaded successfully!")

    def auto_load_assets(self):
        """Auto-load images from assets folder for development"""
        assets_path = os.path.join(os.path.dirname(__file__), "assets")
        if os.path.exists(assets_path) and os.path.isdir(assets_path):
            image_files = [os.path.join(assets_path, f) for f in os.listdir(assets_path)
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            if image_files:
                # Sort to maintain consistent order
                image_files.sort()
                self.image_paths.extend(image_files)
                self.refresh_grid()

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
        self.clear_grid_selection()
        self.canvas.clear_all()

    def adjust_grid_size(self):
        """Adjust the grid size based on input values"""
        rows = self.rows_input.value()
        columns = self.columns_input.value()
        self.canvas.set_grid_dimensions(rows, columns)

    def toggle_select_mode(self):
        """Toggle between select mode and view mode"""
        self.select_mode = not self.select_mode
        if self.select_mode:
            self.select_all_btn.setVisible(True)
            self.update_select_all_button()
        else:
            self.select_all_btn.setVisible(False)
            # Clear selection when exiting select mode
            self.clear_selection()
    
    def select_single(self, file_path):
        self.clear_selection()
        self.selected_paths.add(file_path)
        self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
        self.update_select_all_button()
    
    def toggle_selection(self, file_path):
        if file_path in self.selected_paths:
            self.selected_paths.remove(file_path)
            self.image_labels[file_path].set_selected(False)
        else:
            self.selected_paths.add(file_path)
            self.image_labels[file_path].set_selected(True)
        self.last_selected_index = self.image_paths.index(file_path)
        self.update_delete_button()
        self.update_select_all_button()
    
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
        self.update_select_all_button()
    
    def clear_selection(self):
        for path in self.selected_paths:
            if path in self.image_labels:
                self.image_labels[path].set_selected(False)
        self.selected_paths.clear()
        self.update_delete_button()
        self.update_select_all_button()

    def toggle_select_all(self):
        """Toggle between selecting all and deselecting all images"""
        if len(self.selected_paths) == len(self.image_paths) and len(self.image_paths) > 0:
            # All are selected, so deselect all
            self.clear_selection()
        else:
            # Not all are selected, so select all
            for path in self.image_paths:
                self.selected_paths.add(path)
                if path in self.image_labels:
                    self.image_labels[path].set_selected(True)
            self.update_delete_button()
            self.update_select_all_button()

    def update_select_all_button(self):
        """Update the Select All button text based on current selection"""
        if len(self.selected_paths) == len(self.image_paths) and len(self.image_paths) > 0:
            self.select_all_btn.setText("Deselect All")
        else:
            self.select_all_btn.setText("Select All")
    
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

    def toggle_grid_selection(self, grid_pos):
        """Toggle selection of a grid tile"""
        if grid_pos not in self.canvas.tiles:
            return

        tile = self.canvas.tiles[grid_pos]

        if grid_pos in self.selected_grid_tiles:
            self.selected_grid_tiles.remove(grid_pos)
            tile.set_selected(False)
        else:
            self.selected_grid_tiles.add(grid_pos)
            tile.set_selected(True)

        self.last_selected_grid_pos = grid_pos

    def select_grid_range(self, grid_pos):
        """Select range of grid tiles from last selected to current"""
        if self.last_selected_grid_pos is None:
            self.toggle_grid_selection(grid_pos)
            return

        # Get all tile positions sorted by row then column
        all_positions = sorted(self.canvas.tiles.keys(), key=lambda p: (p[1], p[0]))

        try:
            start_idx = all_positions.index(self.last_selected_grid_pos)
            end_idx = all_positions.index(grid_pos)

            # Select range
            for i in range(min(start_idx, end_idx), max(start_idx, end_idx) + 1):
                pos = all_positions[i]
                if pos not in self.selected_grid_tiles:
                    self.selected_grid_tiles.add(pos)
                    self.canvas.tiles[pos].set_selected(True)
        except ValueError:
            # Position not found, just toggle current
            self.toggle_grid_selection(grid_pos)

    def clear_grid_selection(self):
        """Clear all grid tile selections"""
        for grid_pos in list(self.selected_grid_tiles):
            if grid_pos in self.canvas.tiles:
                self.canvas.tiles[grid_pos].set_selected(False)
        self.selected_grid_tiles.clear()
        self.last_selected_grid_pos = None

    def remove_from_bank(self, file_path):
        """Remove an image from the bank (e.g., when it's placed on the grid)"""
        if file_path in self.image_paths:
            self.image_paths.remove(file_path)
        if file_path in self.selected_paths:
            self.selected_paths.remove(file_path)
        self.refresh_grid()

    def add_to_bank(self, file_path):
        """Add an image back to the bank (e.g., when returned from grid)"""
        if file_path not in self.image_paths:
            self.image_paths.append(file_path)
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
        self.update_select_all_button()
    
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