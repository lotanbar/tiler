# Testing Instructions for Segfault Fix

## What Was Fixed

**The Bug:** When dragging multiple tiles, the code created NEW tiles on drop but then tried to delete the OLD tiles. However, the check `if tile not in self.tiles.values()` was always True (because new tiles were created), so ALL old tiles were deleted. Some references to these deleted tiles remained, causing segfaults when accessed later.

**The Fix:**
1. Removed the broken check - old tiles are ALWAYS deleted after multi-drag since new ones are created
2. Added comprehensive logging to track tile lifecycle
3. Added safety checks in `update_tile_positions()` and `clear_grid_selection()` to skip deleted tiles
4. Changed `for grid_pos, tile in self.tiles.items()` to use `list()` to avoid dict changes during iteration

## How to Test

### 1. Run the application:
```bash
python3 main.py
```

### 2. Import test images:
- Click "Import Images"
- Navigate to `test_images/` folder
- Select all 50 images (Ctrl+A)
- Click Open

### 3. Test multi-tile drag (the crash scenario):
a. Drag 10-15 images from the bank to the grid
b. Select multiple tiles on the grid (click first, then shift-click last)
c. Drag the selected tiles to a new location
d. Repeat steps b-c several times
e. Zoom in/out with mouse wheel (this triggers `update_tile_positions()`)
f. Pan around with middle mouse button

### 4. Stress test:
a. Drag 20+ tiles to the grid
b. Select all tiles (marquee or click + shift-click)
c. Drag them all at once
d. Immediately zoom/pan
e. Drag them again multiple times

### 5. Check the logs:
```bash
tail -f tiler_debug.log
```

Look for:
- `[TILE-X] Created for ...` - tracks tile creation
- `[TILE-X] deleteLater() called` - tracks tile deletion
- `⚠️ DELETED tile still in self.tiles` - indicates lingering references (should NOT appear after fix)
- Any RuntimeError or Exception messages

## Expected Behavior (After Fix)

✅ No segmentation faults
✅ Multi-tile drag works smoothly
✅ Zoom/pan after drag works without crashes
✅ Old tiles are properly cleaned up
✅ No "DELETED tile" warnings in logs

## What to Watch For

❌ Segmentation fault (core dumped) - THE BUG IS BACK
❌ "DELETED tile still in self.tiles" in logs - lingering reference
❌ RuntimeError about deleted objects - cleanup issue
❌ Application freeze or hang - possible deadlock

## Log Analysis

The log will show the exact sequence:
1. Tiles created with unique IDs
2. Multi-drag initiated
3. Old tiles removed from grid
4. New tiles created at drop location
5. Old tiles deleted via cleanup_multi_drag()
6. No access to deleted tiles afterward

If the crash occurs, the log will show EXACTLY which tile ID caused it and where.
