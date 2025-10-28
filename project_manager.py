"""
Project Manager for Tiler Application
Handles saving and loading puzzle projects in JSON format
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


class ProjectManager:
    """Manages saving and loading of puzzle projects"""

    VERSION = 1
    DEFAULT_EXTENSION = ".tiler"

    @staticmethod
    def save_project(filepath: str, grid_canvas, image_viewer) -> bool:
        """
        Save the current puzzle project to a file

        Args:
            filepath: Path to save the project file
            grid_canvas: InfiniteGridCanvas instance with tile data
            image_viewer: ImageViewer instance with bank data

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Ensure filepath has correct extension
            if not filepath.endswith(ProjectManager.DEFAULT_EXTENSION):
                filepath += ProjectManager.DEFAULT_EXTENSION

            # Build project data structure
            project_data = {
                "version": ProjectManager.VERSION,
                "grid": {
                    "rows": grid_canvas.grid_rows,
                    "columns": grid_canvas.grid_columns,
                    "zoom_scale": grid_canvas.zoom_scale,
                    "pan_offset_x": grid_canvas.pan_offset_x,
                    "pan_offset_y": grid_canvas.pan_offset_y
                },
                "tiles": [],
                "bank": {
                    "image_paths": image_viewer.image_paths
                },
                "ui_state": {
                    "selected_grid_positions": list(image_viewer.selected_grid_tiles),
                    "selected_bank_paths": list(image_viewer.selected_paths)
                }
            }

            # Collect all tiles from grid
            for (grid_x, grid_y), tile in grid_canvas.tiles.items():
                tile_data = {
                    "grid_x": grid_x,
                    "grid_y": grid_y,
                    "file_path": tile.file_path,
                    "original_bank_index": tile.original_bank_index
                }
                project_data["tiles"].append(tile_data)

            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load a puzzle project from a file

        Args:
            filepath: Path to the project file

        Returns:
            Dictionary with project data, or None if load failed
        """
        try:
            # Check file exists
            if not os.path.exists(filepath):
                print(f"Project file not found: {filepath}")
                return None

            # Read and parse JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Validate version
            if project_data.get("version") != ProjectManager.VERSION:
                print(f"Unsupported project version: {project_data.get('version')}")
                return None

            # Validate required fields
            required_fields = ["grid", "tiles", "bank"]
            for field in required_fields:
                if field not in project_data:
                    print(f"Missing required field: {field}")
                    return None

            # Validate image files exist and filter out missing ones
            missing_images = []
            valid_tiles = []

            for tile in project_data["tiles"]:
                if os.path.exists(tile["file_path"]):
                    valid_tiles.append(tile)
                else:
                    missing_images.append(tile["file_path"])

            if missing_images:
                print(f"Warning: {len(missing_images)} image(s) not found:")
                for img in missing_images[:5]:  # Show first 5
                    print(f"  - {img}")
                if len(missing_images) > 5:
                    print(f"  ... and {len(missing_images) - 5} more")

            # Update tiles with valid ones only
            project_data["tiles"] = valid_tiles

            # Filter bank images to only existing files
            valid_bank_paths = [
                path for path in project_data["bank"]["image_paths"]
                if os.path.exists(path)
            ]
            project_data["bank"]["image_paths"] = valid_bank_paths

            return project_data

        except json.JSONDecodeError as e:
            print(f"Error parsing project file: {e}")
            return None
        except Exception as e:
            print(f"Error loading project: {e}")
            return None

    @staticmethod
    def validate_project_data(project_data: Dict[str, Any]) -> bool:
        """
        Validate that project data has the correct structure

        Args:
            project_data: Dictionary with project data

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check version
            if project_data.get("version") != ProjectManager.VERSION:
                return False

            # Check grid data
            grid = project_data.get("grid", {})
            required_grid_fields = ["rows", "columns", "zoom_scale", "pan_offset_x", "pan_offset_y"]
            if not all(field in grid for field in required_grid_fields):
                return False

            # Check tiles are list
            if not isinstance(project_data.get("tiles"), list):
                return False

            # Check each tile has required fields
            for tile in project_data["tiles"]:
                required_tile_fields = ["grid_x", "grid_y", "file_path", "original_bank_index"]
                if not all(field in tile for field in required_tile_fields):
                    return False

            # Check bank data
            bank = project_data.get("bank", {})
            if "image_paths" not in bank or not isinstance(bank["image_paths"], list):
                return False

            return True

        except Exception:
            return False
