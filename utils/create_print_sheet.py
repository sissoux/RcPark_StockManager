"""
Print Sheet Generator
Creates an A4 printable sheet with barcode images arranged in two columns.
"""

import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_print_sheet(barcode_dir, json_file, output_file='member_sheet.png', columns=2):
    """
    Create a printable A4 sheet with barcode images.
    
    Args:
        barcode_dir: Directory containing barcode images
        json_file: JSON file with member data (to maintain order)
        output_file: Output filename for the sheet
        columns: Number of columns (default: 2)
    """
    # A4 size at 300 DPI
    a4_width = 2480  # 210mm at 300 DPI
    a4_height = 3508  # 297mm at 300 DPI
    
    # Margins and spacing
    margin = 80
    spacing = 30
    
    # Load member data to get order
    with open(json_file, 'r', encoding='utf-8') as f:
        members_data = json.load(f)
    
    # Sort members alphabetically by name
    sorted_members = sorted(members_data.items(), key=lambda x: x[1])
    
    # Collect barcode images
    barcode_images = []
    for key, name in sorted_members:
        # Create safe filename
        safe_filename = "".join(c if c.isalnum() else "_" for c in name)
        barcode_path = Path(barcode_dir) / f"{safe_filename}.png"
        
        if barcode_path.exists():
            img = Image.open(barcode_path)
            barcode_images.append((name, img))
        else:
            print(f"Warning: Barcode not found for {name}")
    
    if not barcode_images:
        print("Error: No barcode images found!")
        return
    
    # Calculate dimensions
    available_width = a4_width - (2 * margin) - ((columns - 1) * spacing)
    cell_width = available_width // columns
    
    # Calculate optimal scaling to fit all items on one page
    total_items = len(barcode_images)
    rows = (total_items + columns - 1) // columns
    available_height = a4_height - (2 * margin) - ((rows - 1) * spacing)
    max_cell_height = available_height // rows
    
    # Resize barcodes to fit cells
    resized_barcodes = []
    for name, img in barcode_images:
        # Calculate new dimensions maintaining aspect ratio
        aspect_ratio = img.height / img.width
        new_width = cell_width
        new_height = int(cell_width * aspect_ratio)
        
        # If height is too large, scale down
        if new_height > max_cell_height:
            new_height = max_cell_height
            new_width = int(new_height / aspect_ratio)
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized_barcodes.append((name, resized_img, new_width, new_height))
    
    # Create white background
    sheet = Image.new('RGB', (a4_width, a4_height), 'white')
    
    # Place barcodes
    y_offset = margin
    index = 0
    
    for row in range(rows):
        x_offset = margin
        row_height = 0
        
        for col in range(columns):
            if index >= total_items:
                break
            
            name, barcode_img, img_width, img_height = resized_barcodes[index]
            
            # Calculate x position (center in cell)
            x_pos = x_offset + (cell_width - img_width) // 2
            
            # Paste barcode
            sheet.paste(barcode_img, (x_pos, y_offset))
            
            row_height = max(row_height, img_height)
            x_offset += cell_width + spacing
            index += 1
        
        y_offset += row_height + spacing
    
    # Save the sheet
    sheet.save(output_file, dpi=(300, 300))
    print(f"\n✓ Created print sheet: {output_file}")
    print(f"✓ Sheet contains {index} barcodes in {columns} columns")
    print(f"✓ Total rows: {rows}")
    print(f"✓ Ready to print on A4 paper")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create printable A4 sheet with barcodes')
    parser.add_argument('--barcode-dir', default='barcodes', help='Directory containing barcode images')
    parser.add_argument('--json-file', default='../data/members.json', help='JSON file with member data')
    parser.add_argument('--output', default='member_sheet.png', help='Output filename (default: member_sheet.png)')
    parser.add_argument('--columns', type=int, default=2, help='Number of columns (default: 2)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.barcode_dir):
        print(f"Error: Barcode directory '{args.barcode_dir}' not found!")
        exit(1)
    
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found!")
        exit(1)
    
    create_print_sheet(args.barcode_dir, args.json_file, args.output, args.columns)
