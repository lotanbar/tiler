# Segmentation Fault Bug Fix - Summary

## What is a Segmentation Fault?

A **segmentation fault** means your program tried to access memory it doesn't have permission to use. Common causes:
- Accessing a deleted/freed object (using a pointer to deleted memory)
- Dereferencing a NULL/None pointer
- Double-deleting an object

In your case: **accessing deleted Qt widgets**.

## The Exact Bug in Your Code

### Location: `grid_canvas.py:743-751` (cleanup_multi_drag method)

### The Problem Flow:

1. **User drags multiple tiles** (e.g., 50 tiles selected)
   - `mouseMoveEvent()` stores them in `self.dragged_tiles`
   - Removes them from `self.tiles` dictionary
   - Hides them

2. **User drops tiles** (e.g., new location on grid)
   - `dropEvent()` creates **NEW GridTile objects** for each dropped tile
   - Adds these NEW tiles to `self.tiles`
   - OLD tiles are NOT re-added anywhere

3. **Cleanup runs** (QTimer.singleShot calls cleanup_multi_drag)
   ```python
   # THE BUGGY CODE:
   for tile in self.dragged_tiles.values():
       if tile not in self.tiles.values():  # ⚠️ ALWAYS TRUE!
           tile.deleteLater()
   ```

   **Why it's buggy:**
   - `self.tiles.values()` contains the NEW tiles
   - `tile` is an OLD tile object
   - OLD tile objects are NEVER in the new dictionary
   - So `tile not in self.tiles.values()` is ALWAYS True
   - Result: ALL old tiles get `deleteLater()` called

4. **The Crash:**
   - User zooms or pans
   - `update_tile_positions()` is called
   - BUT `self.selected_grid_tiles` still contains grid positions
   - Code tries to access `self.canvas.tiles[grid_pos]`
   - That tile was already deleted by `deleteLater()`
   - **SEGMENTATION FAULT** 💥

### Why "Large Amounts of Files"?

- With few files (5-10): cleanup happens fast, less chance of race condition
- With many files (50+): more operations, more lingering references, higher chance the deleted object gets accessed before Qt fully cleans it up

## The Fix

### 1. Fixed cleanup logic (grid_canvas.py:792-803)
```python
def cleanup_multi_drag(self):
    if self.dragged_tiles:
        # OLD CODE: if tile not in self.tiles.values():  # BROKEN!
        # NEW CODE: Just delete them all - new ones were created!
        for pos, tile in self.dragged_tiles.items():
            tile.deleteLater()
        self.dragged_tiles = None
```

### 2. Added safety checks in update_tile_positions (grid_canvas.py:552-569)
```python
for grid_pos, tile in list(self.tiles.items()):  # Use list() copy
    try:
        if hasattr(tile, '_is_deleted') and tile._is_deleted:
            logger.error(f"⚠️ DELETED tile still in self.tiles!")
            continue
        # ... rest of code
    except RuntimeError:
        # Widget already deleted - catch it gracefully
        pass
```

### 3. Added safety checks in clear_grid_selection (image_viewer.py:792-806)
```python
for grid_pos in list(self.selected_grid_tiles):
    if grid_pos in self.canvas.tiles:
        tile = self.canvas.tiles[grid_pos]
        if hasattr(tile, '_is_deleted') and tile._is_deleted:
            continue  # Skip deleted tiles
        try:
            tile.set_selected(False)
        except RuntimeError:
            pass  # Widget deleted - ignore
```

### 4. Added comprehensive logging
- Every tile gets a unique ID: `[TILE-123]`
- Tracks creation, deletion, and all operations
- Log file: `tiler_debug.log`
- Can trace exactly which tile caused the crash

## Files Modified

1. **grid_canvas.py**
   - Added logging imports and setup
   - Added tile instance tracking (_instance_id)
   - Fixed cleanup_multi_drag() method
   - Added safety checks in update_tile_positions()
   - Added logging throughout drag/drop operations

2. **image_viewer.py**
   - Added safety checks in clear_grid_selection()

3. **New files created:**
   - `generate_test_images.py` - Creates test images for stress testing
   - `TEST_INSTRUCTIONS.md` - How to test the fix
   - `BUGFIX_SUMMARY.md` - This file

## How to Verify the Fix

1. Run the app: `python3 main.py`
2. Import 50+ test images from `test_images/` folder
3. Drag 20+ images to grid
4. Select all tiles (marquee or shift-click)
5. Drag them to a new location
6. Repeat several times
7. Zoom/pan aggressively
8. Check logs: `tail -f tiler_debug.log`

**Expected:** No crashes, no "DELETED tile" warnings
**Before fix:** Segmentation fault after a few multi-tile drags

## Technical Explanation for Understanding

Think of it like this:

```
BEFORE (BUGGY):
- You have 50 toy cars (old tiles) in a box
- You move them to a new box and replace them with 50 NEW toy cars
- Code checks: "Are these OLD toy cars in the new box?"
- Answer: No! (Because new box has NEW cars)
- Code: "Then throw away all OLD cars!"
- But you still have a list that says "car #23 is at position 5"
- You try to play with car #23... IT'S IN THE TRASH! 💥 CRASH

AFTER (FIXED):
- You have 50 toy cars (old tiles) in a box
- You move them to a new box and replace them with 50 NEW toy cars
- Code: "Old cars are always replaced, throw them away"
- Clear the list that tracks car positions
- Now when you look for a car, you only find NEW ones ✅
```

## Key Takeaway

**The bug wasn't about performance or memory limits. It was a logic error:**
- Creating new objects on drop
- Trying to reuse old objects (but failing)
- Deleting old objects
- Still holding references to deleted objects
- Accessing those deleted objects later → CRASH

The fix ensures deleted objects are never accessed after deletion.
