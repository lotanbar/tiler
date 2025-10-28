#!/usr/bin/env python3
"""Generate test images for stress testing the tiler"""

from PIL import Image, ImageDraw, ImageFont
import os

def generate_test_images(count=100, output_dir="test_images"):
    """Generate test images with numbers"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(count):
        # Create a colorful image
        img = Image.new('RGB', (200, 200), color=(
            (i * 37) % 256,
            (i * 73) % 256,
            (i * 113) % 256
        ))

        # Draw the number
        draw = ImageDraw.Draw(img)
        text = str(i)

        # Draw large text
        try:
            # Try to use a larger font if available
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        except:
            font = ImageFont.load_default()

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        position = ((200 - text_width) // 2, (200 - text_height) // 2)
        draw.text(position, text, fill='white', font=font)

        # Save
        filepath = os.path.join(output_dir, f"test_{i:03d}.png")
        img.save(filepath)

    print(f"Generated {count} test images in {output_dir}/")

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    generate_test_images(count)
