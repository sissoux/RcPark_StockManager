# Stock Manager - Association Beverage Management System

A simple barcode-based stock management application for small associations. Members can purchase beverages by scanning their member card, product barcode, and payment method - all without clicking any buttons!

## Features

- **Ultra-simple barcode scanning workflow**: Scan member → Scan product → Scan payment method
- **No clicks required**: Everything is done via barcode scanner
- **Real-time display**: Shows current order status and last 5 transactions
- **Transaction logging**: All purchases saved to CSV file with timestamps
- **Data extraction**: Filter and export transactions by date range

## Setup

### Prerequisites

- Python 3.6 or higher (with tkinter)
- Barcode scanner configured as keyboard input device

### Installation

1. Clone or download this repository
2. No additional packages needed - uses only Python standard library!

### Configuration

The application uses three JSON configuration files in the `data/` folder:

#### 1. `data/members.json`
Maps member barcodes to names:
```json
{
  "1234567890": "John Doe",
  "0987654321": "Jane Smith"
}
```

#### 2. `data/products.json`
Maps product barcodes to names and prices:
```json
{
  "COKE001": {
    "name": "Coca-Cola",
    "price": 1.50
  },
  "WATER001": {
    "name": "Water",
    "price": 1.00
  }
}
```

#### 3. `data/payment_methods.json`
Maps payment barcodes to payment method names:
```json
{
  "PAY_PAYPAL": "PayPal",
  "PAY_CASH": "Cash",
  "PAY_SUMUP": "SumUp"
}
```

**Important**: Edit these files to match your actual barcodes!

## Usage

### Starting the Application

Run the application:
```bash
python stock_manager.py
```

### Making a Purchase

The workflow is simple - just scan 3 barcodes in order:

1. **Scan member barcode** - Identifies who is making the purchase
2. **Scan product barcode** - Selects the beverage
3. **Scan payment method barcode** - Completes and records the transaction

The GUI shows:
- Current order status (member, product, amount)
- Last 5 transactions
- Status messages in the window title

### Extracting Data

Click the "Extract Data" button to:
- Filter transactions by date range
- View filtered results
- Export filtered data to CSV file

### Resetting an Order

If you need to cancel the current order, click the "Reset Order" button.

## File Structure

```
Stock manager/
├── stock_manager.py          # Main application
├── requirements.txt           # Python dependencies (none needed)
├── README.md                  # This file
└── data/
    ├── members.json           # Member barcodes
    ├── products.json          # Product barcodes and prices
    ├── payment_methods.json   # Payment method barcodes
    └── transactions.csv       # Transaction log (auto-created)
```

## Transaction Data

Transactions are stored in `data/transactions.csv` with the following fields:
- Timestamp (YYYY-MM-DD HH:MM:SS)
- Member name
- Product name
- Amount (€)
- Payment method

## Tips

### Barcode Scanner Setup

- Configure your barcode scanner to act as a keyboard input device
- Make sure it sends an "Enter" keypress after each scan
- Test your scanner with a text editor first to ensure it works properly

### Creating Barcodes

You can use free online barcode generators to create printable barcodes:
- Use Code 128 or Code 39 format
- Print member cards, product labels, and payment method cards
- Laminate for durability

### Customization

Edit the JSON files to:
- Add/remove members
- Add/remove products
- Change prices
- Add/remove payment methods

## Troubleshooting

**Barcode not recognized**: Check that the barcode exists in the appropriate JSON file

**Scanner not working**: Ensure scanner is configured for keyboard emulation with Enter key after scan

**Application won't start**: Make sure Python 3.6+ is installed with tkinter support

## License

Free to use for non-commercial purposes.
