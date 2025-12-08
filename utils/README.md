# Barcode Generator Utility

This utility generates barcode images from a member list text file or JSON file.

## Installation

First, install the required dependencies:

```powershell
pip install -r ..\requirements.txt
```

## Usage

### Generate from Member List (TXT file)

The recommended way is to use a text file with one member name per line:

```powershell
python generate_barcodes.py ..\MemberList.txt --purge
```

This will:
1. Read member names from `MemberList.txt`
2. Create/update `data/members.json` with encoded keys (format: MEM_XXX)
3. Purge the `barcodes` folder
4. Generate barcode images for all members

**Key Format:**
- `MEM_` + First letter of first name + First 2 letters of last name
- Example: "Alexis Damiens" → `MEM_ADA`
- Example: "Paul Brocq" → `MEM_PBR`

### Generate from Existing JSON

You can also generate barcodes from an existing JSON file:

```powershell
python generate_barcodes.py ..\data\members.json
```

### Custom Options

```powershell
# Specify custom output directory
python generate_barcodes.py ..\MemberList.txt --output-dir "my_barcodes"

# Specify custom JSON output location
python generate_barcodes.py ..\MemberList.txt --json-output "custom_members.json"

# Add prefix to barcode data
python generate_barcodes.py ..\MemberList.txt --prefix "CLUB_"

# Purge output directory before generating (recommended)
python generate_barcodes.py ..\MemberList.txt --purge

# Specify barcode type (default is code128)
python generate_barcodes.py ..\MemberList.txt --barcode-type "code39"
```

## Output Format

Each barcode image will contain:
1. **Name** (at the top) - The person's full name
2. **Barcode graphic** (in the middle) - Visual barcode representation
3. **Encoded data** (at the bottom) - The key from the JSON file (e.g., 3228021170039)

### Example

For a member "Alexis Damiens", the generated image will show:
```
Alexis Damiens
[BARCODE IMAGE]
MEM_ADA
```

For "Paul Brocq":
```
Paul Brocq
[BARCODE IMAGE]
MEM_PBR
```

## Input File Formats

### Member List (TXT)

A text file with one member name per line:
```
Alexis Damiens
Philippe Damiens
Tony Masclet
Paul Brocq
```

### Members JSON

The JSON file is automatically created with this format:
```json
{
  "MEM_ADA": "Alexis Damiens",
  "MEM_PHD": "Philippe Damiens",
  "MEM_TMA": "Tony Masclet",
  "MEM_PBR": "Paul Brocq"
}
```

Keys are generated as: `MEM_` + first letter of first name + first 2 letters of last name (uppercase).

## Supported Barcode Types

- code128 (default, recommended)
- code39
- ean13
- ean8
- upca
- And others supported by the python-barcode library

## Notes

- Use `--purge` flag to clean the barcodes directory before generating new ones
- Generated filenames are sanitized versions of member names
- Keys are automatically generated in format: MEM_XXX (first initial + first 2 letters of last name)
- You can add an optional prefix using the `--prefix` argument
- All barcodes are saved as PNG images
