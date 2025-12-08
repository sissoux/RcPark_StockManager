"""
Barcode Generator Utility
Generates barcode images from a member list text file.
Creates members.json with encoded keys (MEM_XXX format) and generates barcode images.
Each barcode image will display:
- Name (at the top)
- Barcode graphic
- Encoded data (below the barcode)
"""

import json
import os
import shutil
import unicodedata
from pathlib import Path
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont


def remove_accents(text):
    """
    Remove accents from unicode string.
    
    Args:
        text: String potentially containing accented characters
        
    Returns:
        String with accents removed
    """
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def generate_member_key(name):
    """
    Generate a member key from a name in format MEM_XXX.
    Format: MEM_ + First letter of first name + First two letters of last name
    
    Args:
        name: Full name (e.g., "Alexis Damiens" or "paul brocq")
        
    Returns:
        String in format MEM_XXX (e.g., "MEM_ADA" or "MEM_PBR")
    """
    # Remove accents and convert to uppercase
    normalized_name = remove_accents(name.strip()).upper()
    parts = normalized_name.split()
    
    if len(parts) >= 2:
        # First letter of first name + first 2 letters of last name
        first_initial = parts[0][0]
        last_name_code = parts[-1][:2] if len(parts[-1]) >= 2 else parts[-1]
        return f"MEM_{first_initial}{last_name_code}"
    else:
        # If only one name, use first 3 letters
        single_name = parts[0]
        code = single_name[:3] if len(single_name) >= 3 else single_name
        return f"MEM_{code}"


def load_members_from_txt(txt_file):
    """
    Load member names from a text file (one name per line).
    
    Args:
        txt_file: Path to text file containing member names
        
    Returns:
        List of member names
    """
    with open(txt_file, 'r', encoding='utf-8') as f:
        # Read lines and filter out empty ones
        members = [line.strip() for line in f if line.strip()]
    return members


def create_members_json(txt_file, json_file):
    """
    Create members.json from a text file containing member names.
    
    Args:
        txt_file: Path to text file with member names
        json_file: Path where JSON file will be created
        
    Returns:
        Dictionary with member data
    """
    members = load_members_from_txt(txt_file)
    
    # Sort members alphabetically
    members.sort()
    
    # Create dictionary with MEM_XXX keys
    members_dict = {}
    for name in members:
        key = generate_member_key(name)
        members_dict[key] = name
    
    # Save to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(members_dict, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created {json_file} with {len(members_dict)} members (sorted alphabetically)")
    return members_dict


def load_barcode_data(json_file):
    """
    Load barcode data from JSON file.
    
    Args:
        json_file: Path to JSON file containing barcode data
        
    Returns:
        Dictionary with barcode codes as keys and names as values
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_barcode_with_labels(name, barcode_data, output_path, barcode_type='code128'):
    """
    Create a barcode image with name at top and encoded data at bottom.
    
    Args:
        name: Display name to show at the top
        barcode_data: Data to encode in the barcode
        output_path: Path where the image will be saved
        barcode_type: Type of barcode (default: code128)
    """
    # Generate barcode
    barcode_class = barcode.get_barcode_class(barcode_type)
    
    # Create barcode with ImageWriter
    barcode_instance = barcode_class(barcode_data, writer=ImageWriter())
    
    # Temporarily save barcode without text
    temp_barcode_path = output_path.replace('.png', '_temp')
    barcode_instance.save(temp_barcode_path, {
        'write_text': False,
        'module_height': 10,
        'module_width': 0.3,
        'quiet_zone': 2,
        'font_size': 0,
        'text_distance': 0,
    })
    
    # Load the generated barcode
    barcode_img = Image.open(f"{temp_barcode_path}.png")
    
    # Calculate dimensions for final image
    barcode_width, barcode_height = barcode_img.size
    top_margin = 60
    bottom_margin = 50
    final_height = barcode_height + top_margin + bottom_margin
    
    # Create new image with white background
    final_img = Image.new('RGB', (barcode_width, final_height), 'white')
    draw = ImageDraw.Draw(final_img)
    
    # Try to use a nicer font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        data_font = ImageFont.truetype("arial.ttf", 16)
    except:
        title_font = ImageFont.load_default()
        data_font = ImageFont.load_default()
    
    # Draw name at top (centered)
    name_bbox = draw.textbbox((0, 0), name, font=title_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = (barcode_width - name_width) // 2
    draw.text((name_x, 15), name, fill='black', font=title_font)
    
    # Paste barcode in the middle
    final_img.paste(barcode_img, (0, top_margin))
    
    # Draw encoded data at bottom (centered)
    data_bbox = draw.textbbox((0, 0), barcode_data, font=data_font)
    data_width = data_bbox[2] - data_bbox[0]
    data_x = (barcode_width - data_width) // 2
    draw.text((data_x, top_margin + barcode_height + 10), barcode_data, fill='black', font=data_font)
    
    # Save final image
    final_img.save(output_path)
    
    # Clean up temporary file
    os.remove(f"{temp_barcode_path}.png")
    
    print(f"✓ Generated barcode for: {name} -> {output_path}")


def generate_barcodes_from_json(json_file, output_dir='barcodes', prefix='', barcode_type='code128', purge=False):
    """
    Generate barcode images for all entries in a JSON file.
    
    Args:
        json_file: Path to JSON file (e.g., members.json)
        output_dir: Directory where barcode images will be saved
        prefix: Optional prefix to add to codes (default: '')
        barcode_type: Type of barcode to generate (default: 'code128')
        purge: If True, delete and recreate the output directory
    """
    # Create output directory
    output_path = Path(output_dir)
    
    # Purge directory if requested
    if purge and output_path.exists():
        print(f"✓ Purging directory: {output_dir}")
        shutil.rmtree(output_path)
    
    output_path.mkdir(exist_ok=True)
    
    # Load data from JSON
    data = load_barcode_data(json_file)
    
    print(f"\nGenerating barcodes from: {json_file}")
    print(f"Output directory: {output_dir}")
    print(f"Total items: {len(data)}\n")
    
    # Generate barcode for each entry
    for code, name in data.items():
        # Use the key from JSON as the encoded data
        encoded_data = f"{prefix}{code}"
        
        # Create safe filename
        safe_filename = "".join(c if c.isalnum() else "_" for c in name)
        output_file = output_path / f"{safe_filename}.png"
        
        try:
            create_barcode_with_labels(name, encoded_data, str(output_file), barcode_type)
        except Exception as e:
            print(f"✗ Error generating barcode for {name}: {e}")
    
    print(f"\n✓ Barcode generation complete!")
    print(f"✓ Generated {len(data)} barcodes in '{output_dir}' directory")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate barcodes from member list or JSON file')
    parser.add_argument('input_file', help='Path to TXT file (member list) or JSON file (barcode data)')
    parser.add_argument('--output-dir', default='barcodes', help='Output directory for barcode images (default: barcodes)')
    parser.add_argument('--prefix', default='', help='Optional prefix for encoded data (default: none)')
    parser.add_argument('--barcode-type', default='code128', help='Barcode type (default: code128)')
    parser.add_argument('--json-output', default='../data/members.json', help='Path to save/update members.json (default: ../data/members.json)')
    parser.add_argument('--purge', action='store_true', help='Purge output directory before generating barcodes')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found!")
        exit(1)
    
    # Determine if input is TXT or JSON
    if args.input_file.lower().endswith('.txt'):
        print(f"Processing member list from: {args.input_file}\n")
        # Create members.json from TXT file
        members_dict = create_members_json(args.input_file, args.json_output)
        json_file = args.json_output
    elif args.input_file.lower().endswith('.json'):
        print(f"Using existing JSON file: {args.input_file}\n")
        json_file = args.input_file
    else:
        print("Error: Input file must be .txt or .json")
        exit(1)
    
    # Generate barcodes
    generate_barcodes_from_json(
        json_file,
        args.output_dir,
        args.prefix,
        args.barcode_type,
        args.purge
    )

