"""
Stock Manager Application for Association
Barcode-based beverage stock management system
"""

# Debug mode - Set to True to enable debug messages
DEBUG = True

# AZERTY Conversion - Set to True if barcode scanner sends QWERTY on AZERTY keyboard
AZERTY_CONVERT = True

# Admin password for protected operations
ADMIN_PASSWORD = "1234"

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import csv
import os
from pathlib import Path
import qrcode
from PIL import Image, ImageTk
import io
import urllib.request
import urllib.error


def qwerty_to_azerty(text):
    """Convert AZERTY scanner output to correct characters (scanner sends AZERTY but we need QWERTY/numbers)"""
    # Mapping AZERTY characters to their intended values
    # When scanner reads '3' on QWERTY layout, it outputs '"' on AZERTY keyboard
    azerty_to_qwerty_map = {
        # AZERTY top row to numbers
        '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
        '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0',
        # Letters
        'q': 'a', 'a': 'q', 'w': 'z', 'z': 'w',
        'Q': 'A', 'A': 'Q', 'W': 'Z', 'Z': 'W',
        # Special characters
        ')': '-', '°': '_', '^': '[', '$': ']',
        'm': ';', '.': ':', 'ù': "'", '%': '"',
        ';': ',', ':': '.', '!': '/', 'M': '?',
        '*': '\\', 'µ': '|', '²': '`',
        # Shifted AZERTY numbers to shifted QWERTY numbers
        '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
        '6': '^', '7': '&', '8': '*', '9': '(', '0': ')'
    }
    return ''.join(azerty_to_qwerty_map.get(c, c) for c in text)


class StockManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestionnaire de Stock - RC PARK")
        # Don't set fixed geometry - let it fit content
        
        # Set window icon (if icon.ico exists in the same directory)
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                if DEBUG:
                    print(f"Could not load icon: {e}")
        
        # Data files
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.members_file = self.data_dir / "members.json"
        self.products_file = self.data_dir / "products.json"
        self.payment_methods_file = self.data_dir / "payment_methods.json"
        self.transactions_file = self.data_dir / "transactions.csv"
        
        # Load data
        self.members = self.load_json(self.members_file, {})
        self.products = self.load_json(self.products_file, {})
        self.payment_methods = self.load_json(self.payment_methods_file, {})
        
        # Current transaction state
        self.current_member = None
        self.cart = {}  # {barcode: {name, price, quantity}}
        self.current_amount = 0.0
        
        # Initialize transactions file if doesn't exist
        if not self.transactions_file.exists():
            with open(self.transactions_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Member', 'Product', 'Amount', 'Payment Method'])
        
        self.setup_ui()
        
        # Focus on barcode entry
        self.barcode_entry.focus_set()
    
    def load_json(self, filepath, default):
        """Load JSON file or return default if doesn't exist or is corrupted"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # Backup corrupted file if it exists
            if filepath.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = filepath.with_suffix(f'.backup_{timestamp}.json')
                try:
                    import shutil
                    shutil.copy2(filepath, backup_path)
                    if DEBUG:
                        print(f"Backed up corrupted file to: {backup_path}")
                except Exception as backup_error:
                    if DEBUG:
                        print(f"Could not backup file: {backup_error}")
            
            if DEBUG:
                print(f"Error loading {filepath}: {e}. Creating new file with default values.")
        
        # Create file with default values if it doesn't exist or is corrupted
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        
        return default
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0)
        
        # Title
        title_label = ttk.Label(main_frame, text="Gestionnaire de Stock", font=('Inter', 20, 'bold'))
        title_label.grid(row=0, column=0, pady=10)
        
        # Barcode input (hidden)
        barcode_frame = ttk.LabelFrame(main_frame, text="Scanner le code-barres", padding="10")
        barcode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        self.barcode_entry = ttk.Entry(barcode_frame, font=('Inter', 14), width=50)
        self.barcode_entry.grid(row=0, column=0, padx=5)
        self.barcode_entry.bind('<Return>', self.process_barcode)
        
        # Status message display
        status_message_frame = ttk.Frame(main_frame)
        status_message_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_message_label = ttk.Label(status_message_frame, text="Pr\u00eat \u00e0 scanner", 
                                               font=('Inter', 12, 'bold'), foreground='blue')
        self.status_message_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        status_message_frame.columnconfigure(0, weight=1)
        
        # Timer ID for status messages
        self.status_timer_id = None
        
        # Current order status
        status_frame = ttk.LabelFrame(main_frame, text="Commande en cours", padding="10")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(3, weight=1)
        
        # Member info
        member_info_frame = ttk.Frame(status_frame)
        member_info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(member_info_frame, text="Membre:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.member_label = ttk.Label(member_info_frame, text="---", font=('Inter', 12, 'bold'), foreground='blue')
        self.member_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        
        ttk.Label(member_info_frame, text="Total:").grid(row=0, column=2, sticky=tk.E, pady=2, padx=(20, 0))
        self.amount_label = ttk.Label(member_info_frame, text="0.00 €", font=('Inter', 14, 'bold'), foreground='red')
        self.amount_label.grid(row=0, column=3, sticky=tk.E, padx=10, pady=2)
        member_info_frame.columnconfigure(2, weight=1)
        
        # Cart items list
        cart_list_frame = ttk.Frame(status_frame)
        cart_list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        status_frame.rowconfigure(1, weight=1)
        
        columns = ('Product', 'Price', 'Qty', 'Total')
        self.cart_tree = ttk.Treeview(cart_list_frame, columns=columns, show='headings', height=4)
        
        self.cart_tree.heading('Product', text='Produits')
        self.cart_tree.heading('Price', text='Prix')
        self.cart_tree.heading('Qty', text='Qté')
        self.cart_tree.heading('Total', text='Total')
        
        self.cart_tree.column('Product', width=200)
        self.cart_tree.column('Price', width=80)
        self.cart_tree.column('Qty', width=50)
        self.cart_tree.column('Total', width=80)
        
        cart_scrollbar = ttk.Scrollbar(cart_list_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscroll=cart_scrollbar.set)
        
        self.cart_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        cart_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        cart_list_frame.columnconfigure(0, weight=1)
        cart_list_frame.rowconfigure(0, weight=1)
        
        # Reset button in order panel
        reset_button_frame = ttk.Frame(status_frame)
        reset_button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        ttk.Button(reset_button_frame, text="R\u00e9initialiser Commande", command=self.reset_order).pack(side=tk.RIGHT)
        
        # Recent transactions
        trans_frame = ttk.LabelFrame(main_frame, text="5 derni\u00e8res transactions", padding="10")
        trans_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(4, weight=1)
        
        # Treeview for transactions
        columns = ('Time', 'Member', 'Product', 'Amount', 'Payment')
        self.trans_tree = ttk.Treeview(trans_frame, columns=columns, show='headings', height=5)
        
        self.trans_tree.heading('Time', text='Date & Heure')
        self.trans_tree.heading('Member', text='Membre')
        self.trans_tree.heading('Product', text='Produits')
        self.trans_tree.heading('Amount', text='Montant')
        self.trans_tree.heading('Payment', text='Paiement')
        
        self.trans_tree.column('Time', width=150)
        self.trans_tree.column('Member', width=150)
        self.trans_tree.column('Product', width=150)
        self.trans_tree.column('Amount', width=100)
        self.trans_tree.column('Payment', width=100)
        
        scrollbar = ttk.Scrollbar(trans_frame, orient=tk.VERTICAL, command=self.trans_tree.yview)
        self.trans_tree.configure(yscroll=scrollbar.set)
        
        self.trans_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        trans_frame.columnconfigure(0, weight=1)
        trans_frame.rowconfigure(0, weight=1)
        
        # Low stock products
        low_stock_frame = ttk.LabelFrame(main_frame, text="Produits en stock faible (< 5)", padding="10")
        low_stock_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Treeview for low stock products
        low_stock_columns = ('Product', 'Stock', 'Price')
        self.low_stock_tree = ttk.Treeview(low_stock_frame, columns=low_stock_columns, show='headings', height=3)
        
        self.low_stock_tree.heading('Product', text='Produit')
        self.low_stock_tree.heading('Stock', text='Stock')
        self.low_stock_tree.heading('Price', text='Prix')
        
        self.low_stock_tree.column('Product', width=250)
        self.low_stock_tree.column('Stock', width=80)
        self.low_stock_tree.column('Price', width=80)
        
        low_stock_scrollbar = ttk.Scrollbar(low_stock_frame, orient=tk.VERTICAL, command=self.low_stock_tree.yview)
        self.low_stock_tree.configure(yscroll=low_stock_scrollbar.set)
        
        self.low_stock_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        low_stock_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        low_stock_frame.columnconfigure(0, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, pady=10)
        
        ttk.Button(button_frame, text="Ajouter/Modifier Article", command=self.protected_add_article).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Exporter Transactions", command=self.protected_extract_data).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Exporter Stock", command=self.protected_export_stock).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Exporter Statistiques", command=self.protected_export_stats).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="Gérer Code-Barres", command=self.protected_manage_barcodes).grid(row=0, column=4, padx=5)
        
        # Load recent transactions and low stock
        self.load_recent_transactions()
        self.update_low_stock_display()
    
    def verify_admin_password(self):
        """Verify admin password before allowing protected operations"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Authentification")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0)
        
        ttk.Label(frame, text="Mot de passe administrateur:", font=('Inter', 11)).grid(row=0, column=0, pady=(0, 10))
        
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", font=('Inter', 12), width=20)
        password_entry.grid(row=1, column=0, pady=(0, 15))
        password_entry.focus_set()
        
        result = {'authenticated': False}
        
        def check_password():
            if password_var.get() == ADMIN_PASSWORD:
                result['authenticated'] = True
                dialog.destroy()
            else:
                messagebox.showerror("Erreur", "Mot de passe incorrect")
                password_entry.delete(0, tk.END)
                password_entry.focus_set()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0)
        ttk.Button(button_frame, text="OK", command=check_password).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Annuler", command=on_cancel).grid(row=0, column=1, padx=5)
        
        password_entry.bind('<Return>', lambda e: check_password())
        
        dialog.wait_window()
        return result['authenticated']
    
    def protected_add_article(self):
        """Protected wrapper for add article dialog"""
        if self.verify_admin_password():
            self.show_add_article_dialog()
    
    def protected_extract_data(self):
        """Protected wrapper for extract data dialog"""
        if self.verify_admin_password():
            self.show_extract_dialog()
    
    def protected_export_stock(self):
        """Protected wrapper for export stock"""
        if self.verify_admin_password():
            self.export_stock()
    
    def protected_export_stats(self):
        """Protected wrapper for export statistics"""
        if self.verify_admin_password():
            self.show_stats_dialog()
    
    def protected_manage_barcodes(self):
        """Protected wrapper for manage barcodes"""
        if self.verify_admin_password():
            self.show_manage_barcodes_dialog()
    
    def process_barcode(self, event=None):
        """Process scanned barcode"""
        barcode = self.barcode_entry.get().strip()
        
        if not barcode:
            self.barcode_entry.delete(0, tk.END)
            return
        
        # Convert QWERTY to AZERTY if option is enabled
        if AZERTY_CONVERT:
            original_barcode = barcode
            barcode = qwerty_to_azerty(barcode)
            if DEBUG:
                print(f"AZERTY conversion: '{original_barcode}' -> '{barcode}'")
        
        # Clear the entry field immediately after reading
        self.barcode_entry.delete(0, tk.END)
        
        # Debug: Print barcode and its representation
        if DEBUG:
            print(f"Scanned barcode: '{barcode}'")
            print(f"Barcode repr: {repr(barcode)}")
            print(f"Available payment methods: {list(self.payment_methods.keys())}")
        
        # Check if it's a member
        if barcode in self.members:
            self.current_member = self.members[barcode]
            self.member_label.config(text=self.current_member)
            self.show_status(f"Membre: {self.current_member}", "info")
            return
        
        # Check if it's a product
        if barcode in self.products:
            if not self.current_member:
                self.show_status("Veuillez scanner le code-barres du membre d'abord!", "warning")
                return
            
            product_name = self.products[barcode]["name"]
            product_price = self.products[barcode]["price"]
            
            # Add to cart or increase quantity
            if barcode in self.cart:
                self.cart[barcode]["quantity"] += 1
                self.show_status(f"Ajouté {product_name} (x{self.cart[barcode]['quantity']})", "info")
            else:
                self.cart[barcode] = {
                    "name": product_name,
                    "price": product_price,
                    "quantity": 1
                }
                self.show_status(f"Ajouté {product_name} au panier", "info")
            
            self.update_cart_display()
            return
        
        # Check if it's a payment method
        if barcode in self.payment_methods:
            if not self.current_member:
                self.show_status("Veuillez scanner le code-barres du membre d'abord!", "warning")
                return
            
            if len(self.cart) == 0:
                self.show_status("Le panier est vide! Ajoutez des produits d'abord.", "warning")
                return
            
            payment_method = self.payment_methods[barcode]
            
            # Show PayPal QR code if PayPal is selected
            if payment_method.lower() == "paypal":
                self.show_paypal_qr(payment_method)
            else:
                # Confirm payment for other methods
                confirm = messagebox.askyesno(
                    "Confirmer le Paiement",
                    f"Membre: {self.current_member}\n"
                    f"Total: {self.current_amount:.2f} €\n"
                    f"Paiement: {payment_method}\n\n"
                    f"Confirmer la transaction?"
                )
                
                if confirm:
                    self.save_transaction(payment_method)
                    self.show_status(f"Transaction enregistrée! Paiement: {payment_method}", "success")
                    self.reset_order()
                else:
                    self.show_status("Paiement annulé", "warning")
            return
        
        # Unknown barcode
        if DEBUG:
            print(f"Barcode not found in any category")
        self.show_status(f"Code-barres inconnu: {barcode}", "error")
    
    def update_cart_display(self):
        """Update the cart display with current items"""
        # Clear existing items
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Calculate total and add items
        total = 0.0
        for barcode, item in self.cart.items():
            item_total = item["price"] * item["quantity"]
            total += item_total
            self.cart_tree.insert('', tk.END, values=(
                item["name"],
                f"{item['price']:.2f} €",
                item["quantity"],
                f"{item_total:.2f} €"
            ))
        
        self.current_amount = total
        self.amount_label.config(text=f"{total:.2f} €")
    
    def save_transaction(self, payment_method):
        """Save transaction to CSV file and update stock"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build product list string (use semicolon to avoid CSV separator conflict)
        product_list = []
        for barcode, item in self.cart.items():
            product_list.append(f"{item['name']} (x{item['quantity']})")
        product_desc = "; ".join(product_list)
        
        # Save as single transaction entry
        with open(self.transactions_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                self.current_member,
                product_desc,
                f"{self.current_amount:.2f}",
                payment_method
            ])
        
        # Update stock for each item
        for barcode, item in self.cart.items():
            if barcode in self.products:
                current_stock = self.products[barcode].get("stock", 0)
                new_stock = current_stock - item["quantity"]
                self.products[barcode]["stock"] = new_stock
                
                if DEBUG:
                    print(f"Stock updated for {item['name']}: {current_stock} -> {new_stock}")
        
        # Save updated products
        self.save_products()
        
        # Update low stock display
        self.update_low_stock_display()
        
        # Reload recent transactions
        self.load_recent_transactions()
    
    def reset_order(self):
        """Reset current order"""
        self.current_member = None
        self.cart = {}
        self.current_amount = 0.0
        
        self.member_label.config(text="---")
        self.amount_label.config(text="0.00 €")
        
        # Clear cart display
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        self.barcode_entry.focus_set()
    
    def load_recent_transactions(self):
        """Load last 5 transactions into the treeview"""
        # Clear existing items
        for item in self.trans_tree.get_children():
            self.trans_tree.delete(item)
        
        # Read transactions
        if self.transactions_file.exists():
            with open(self.transactions_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                transactions = list(reader)
            
            # Get last 5 transactions
            recent = transactions[-5:] if len(transactions) > 5 else transactions
            recent.reverse()
            
            for trans in recent:
                if len(trans) == 5:
                    # Show full date and time
                    self.trans_tree.insert('', tk.END, values=(trans[0], trans[1], trans[2], trans[3] + ' \u20ac', trans[4]))
    
    def update_low_stock_display(self):
        """Update the low stock products display"""
        # Clear existing items
        for item in self.low_stock_tree.get_children():
            self.low_stock_tree.delete(item)
        
        # Find products with stock < 5
        low_stock_threshold = 5
        low_stock_products = []
        
        for barcode, product in self.products.items():
            stock = product.get("stock", 0)
            if stock < low_stock_threshold:
                low_stock_products.append({
                    "name": product["name"],
                    "stock": stock,
                    "price": product["price"]
                })
        
        # Sort by stock (lowest first)
        low_stock_products.sort(key=lambda x: x["stock"])
        
        # Add to treeview with color coding
        for product in low_stock_products:
            item_id = self.low_stock_tree.insert('', tk.END, values=(
                product["name"],
                str(product["stock"]),
                f"{product['price']:.2f} \u20ac"
            ))
            
            # Color code based on stock level
            if product["stock"] <= 0:
                self.low_stock_tree.item(item_id, tags=('critical',))
            elif product["stock"] < 3:
                self.low_stock_tree.item(item_id, tags=('warning',))
        
        # Configure tag colors
        self.low_stock_tree.tag_configure('critical', foreground='red', font=('Inter', 10, 'bold'))
        self.low_stock_tree.tag_configure('warning', foreground='orange', font=('Inter', 10, 'bold'))
    
    def export_stock(self):
        """Export current stock to CSV file - show preview window first"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Exporter Stock")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Title
        ttk.Label(main_frame, text="Aperçu du Stock", 
                  font=('Inter', 14, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Search/filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filtrer", padding="10")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Scanner ou chercher:").grid(row=0, column=0, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=search_var, font=('Inter', 11), width=40)
        search_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        filter_frame.columnconfigure(1, weight=1)
        
        # Stock treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(2, weight=1)
        
        columns = ('Barcode', 'Product', 'Price', 'Stock')
        stock_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        stock_tree.heading('Barcode', text='Code-barres')
        stock_tree.heading('Product', text='Produit')
        stock_tree.heading('Price', text='Prix (€)')
        stock_tree.heading('Stock', text='Stock')
        
        stock_tree.column('Barcode', width=150)
        stock_tree.column('Product', width=250)
        stock_tree.column('Price', width=100)
        stock_tree.column('Stock', width=80)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=stock_tree.yview)
        stock_tree.configure(yscroll=scrollbar.set)
        
        stock_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Store all products data
        all_products = []
        for barcode, product in self.products.items():
            all_products.append({
                'barcode': barcode,
                'name': product["name"],
                'price': product['price'],
                'stock': product.get("stock", 0)
            })
        
        # Sort by product name
        all_products.sort(key=lambda x: x['name'])
        
        def populate_tree(filter_text=""):
            """Populate tree with filtered data"""
            # Clear existing items
            for item in stock_tree.get_children():
                stock_tree.delete(item)
            
            # Convert filter to lowercase for case-insensitive search
            filter_lower = filter_text.lower()
            
            # Apply AZERTY conversion to filter if needed
            if AZERTY_CONVERT and filter_text:
                converted_filter = qwerty_to_azerty(filter_text)
                if DEBUG:
                    print(f"Filter conversion: '{filter_text}' -> '{converted_filter}'")
                filter_lower = converted_filter.lower()
            
            # Add filtered products
            count = 0
            for product in all_products:
                if not filter_text or (
                    filter_lower in product['barcode'].lower() or
                    filter_lower in product['name'].lower()
                ):
                    stock_tree.insert('', tk.END, values=(
                        product['barcode'],
                        product['name'],
                        f"{product['price']:.2f}",
                        product['stock']
                    ))
                    count += 1
            
            # Update status
            status_label.config(text=f"{count} produit(s) affiché(s)")
        
        def on_search_change(*args):
            """Called when search text changes"""
            populate_tree(search_var.get().strip())
        
        def on_search_enter(event=None):
            """Called when Enter is pressed in search field"""
            search_text = search_entry.get().strip()
            if search_text and AZERTY_CONVERT:
                # Convert and update the search field
                converted = qwerty_to_azerty(search_text)
                search_var.set(converted)
            populate_tree(search_var.get().strip())
        
        # Bind search events
        search_var.trace('w', on_search_change)
        search_entry.bind('<Return>', on_search_enter)
        search_entry.focus_set()
        
        # Status label
        status_label = ttk.Label(main_frame, text="", font=('Inter', 9), foreground='blue')
        status_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        def do_export():
            """Export the currently displayed (filtered) stock"""
            from tkinter import filedialog
            
            # Create default filename with timestamp
            export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"stock_export_{export_timestamp}.csv"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
                parent=dialog
            )
            
            if filename:
                try:
                    # Get visible items from tree
                    items = stock_tree.get_children()
                    
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # Write header
                        writer.writerow(['Code-barres', 'Produit', 'Prix (€)', 'Stock'])
                        
                        # Write visible products
                        for item in items:
                            values = stock_tree.item(item)['values']
                            writer.writerow(values)
                    
                    messagebox.showinfo("Succès", f"Stock exporté vers {filename}\\n\\n{len(items)} produit(s) exporté(s)", parent=dialog)
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Érreur", f"Échec de l'export: {str(e)}", parent=dialog)
        
        ttk.Button(button_frame, text="Exporter", command=do_export).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Annuler", command=dialog.destroy).grid(row=0, column=1, padx=5)
        
        # Initial population
        populate_tree()
    
    def show_status(self, message, status_type):
        """Show status message in the status display area"""
        if status_type == "success":
            color = "green"
        elif status_type == "warning":
            color = "orange"
        elif status_type == "error":
            color = "red"
        else:
            color = "blue"
        
        # Update status message label
        self.status_message_label.config(text=message, foreground=color)
        
        # Cancel any existing timer
        if self.status_timer_id:
            self.root.after_cancel(self.status_timer_id)
        
        # Set timer to clear message after 10 seconds (only for errors/warnings)
        if status_type in ["error", "warning"]:
            self.status_timer_id = self.root.after(10000, lambda: self.status_message_label.config(
                text="Prêt à scanner", foreground="blue"
            ))
        if status_type == "success":
            color = "green"
        elif status_type == "warning":
            color = "orange"
        elif status_type == "error":
            color = "red"
        else:
            color = "blue"
        
        # Update status message label
        self.status_message_label.config(text=message, foreground=color)
        
        # Cancel any existing timer
        if self.status_timer_id:
            self.root.after_cancel(self.status_timer_id)
        
        # Set timer to clear message after 10 seconds (only for errors/warnings)
        if status_type in ["error", "warning"]:
            self.status_timer_id = self.root.after(10000, lambda: self.status_message_label.config(
                text="Pr\u00eat \u00e0 scanner", foreground="blue"
            ))
    
    def show_paypal_qr(self, payment_method):
        """Show PayPal QR code for payment"""
        # Create PayPal payment link with dot for decimal separator
        amount_str = f"{self.current_amount:.2f}"
        paypal_url = f"https://paypal.me/rcpark59193/{amount_str}"
        
        # Output the link to console only in debug mode
        if DEBUG:
            print(f"PayPal payment link: {paypal_url}")
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(paypal_url)
        qr.make(fit=True)
        
        # Generate QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Paiement PayPal")
        dialog.geometry("400x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Title
        ttk.Label(main_frame, text="Scanner pour payer avec PayPal", 
                  font=('Inter', 14, 'bold')).grid(row=0, column=0, pady=(0, 10))
        
        # Payment details
        details_frame = ttk.Frame(main_frame)
        details_frame.grid(row=1, column=0, pady=(0, 20))
        
        ttk.Label(details_frame, text=f"Membre: {self.current_member}", 
                  font=('Inter', 11)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(details_frame, text=f"Montant: {self.current_amount:.2f} €", 
                  font=('Inter', 11, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Convert PIL image to Tkinter PhotoImage
        # Resize for display
        qr_img = qr_img.resize((300, 300), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(qr_img)
        
        # Display QR code
        qr_label = ttk.Label(main_frame, image=photo)
        qr_label.image = photo  # Keep a reference
        qr_label.grid(row=2, column=0, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(0, 10))
        
        def confirm_payment():
            self.save_transaction(payment_method)
            self.show_status(f"Transaction enregistrée! Paiement: {payment_method}", "success")
            dialog.destroy()
            self.reset_order()
        
        def cancel_payment():
            self.show_status("Paiement annulé", "warning")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Paiement Effectué", 
                   command=confirm_payment).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Annuler", 
                   command=cancel_payment).grid(row=0, column=1, padx=5)
    
    def save_products(self):
        """Save products to JSON file"""
        try:
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Érreur", f"Échec de l'enregistrement des produits: {str(e)}")
            return False
    
    def show_add_article_dialog(self):
        """Show dialog for adding or updating articles"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter/Modifier Article")
        # Let dialog size fit content
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0)
        
        # Instructions
        ttk.Label(main_frame, text="Scanner ou entrer le code-barres pour ajouter/modifier un article", 
                  font=('Inter', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Barcode input
        barcode_frame = ttk.LabelFrame(main_frame, text="Code-barres", padding="10")
        barcode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        barcode_entry = ttk.Entry(barcode_frame, font=('Inter', 14), width=40)
        barcode_entry.grid(row=0, column=0, padx=5)
        barcode_entry.focus_set()
        
        # Article details frame (initially hidden)
        details_frame = ttk.LabelFrame(main_frame, text="Détails de l'Article", padding="10")
        details_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        details_frame.grid_remove()  # Hide initially
        
        # Name
        ttk.Label(details_frame, text="Nom:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(5, 0))
        name_entry = ttk.Entry(details_frame, font=('Inter', 12), width=30)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Price
        ttk.Label(details_frame, text="Prix (€):").grid(row=1, column=0, sticky=tk.W, pady=5)
        price_entry = ttk.Entry(details_frame, font=('Inter', 12))
        price_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Stock
        stock_frame = ttk.Frame(details_frame)
        stock_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(details_frame, text="Stock:").grid(row=2, column=0, sticky=tk.W, pady=5)
        stock_entry = ttk.Entry(stock_frame, font=('Inter', 12), width=10)
        stock_entry.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(stock_frame, text="+").grid(row=0, column=1, padx=(10, 5))
        add_stock_entry = ttk.Entry(stock_frame, font=('Inter', 12), width=8)
        add_stock_entry.grid(row=0, column=2)
        
        def add_to_stock():
            try:
                current = int(stock_entry.get()) if stock_entry.get().strip() else 0
                to_add = int(add_stock_entry.get()) if add_stock_entry.get().strip() else 0
                new_stock = current + to_add
                stock_entry.delete(0, tk.END)
                stock_entry.insert(0, str(new_stock))
                add_stock_entry.delete(0, tk.END)
                status_label.config(text=f"Ajouté {to_add} au stock. Nouveau stock: {new_stock}", foreground="green")
            except ValueError:
                messagebox.showerror("Érreur", "Veuillez entrer des nombres valides pour le stock")
        
        ttk.Button(stock_frame, text="Ajouter", command=add_to_stock, width=8).grid(row=0, column=3, padx=5)
        
        details_frame.columnconfigure(1, weight=1)
        
        # Status label
        status_label = ttk.Label(main_frame, text="", font=('Inter', 10))
        status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        def fetch_product_info(barcode):
            """Fetch product information from Open Food Facts API"""
            try:
                url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
                with urllib.request.urlopen(url, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    if data.get('status') == 1 and 'product' in data:
                        product = data['product']
                        product_name = product.get('product_name', '')
                        
                        if DEBUG:
                            print(f"Open Food Facts: Found product '{product_name}'.encode('utf-8', 'replace').decode('utf-8')")
                        
                        return product_name
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception) as e:
                if DEBUG:
                    print(f"Open Food Facts API error: {str(e).encode('utf-8', 'replace').decode('utf-8')}")
            
            return None
        
        def process_article_barcode(event=None):
            barcode = barcode_entry.get().strip()
            if not barcode:
                return
            
            # Convert AZERTY to QWERTY if option is enabled
            if AZERTY_CONVERT:
                original_barcode = barcode
                barcode = qwerty_to_azerty(barcode)
                if DEBUG:
                    print(f"AZERTY conversion (article): '{original_barcode}' -> '{barcode}'")
                # Update entry field to show converted barcode
                barcode_entry.delete(0, tk.END)
                barcode_entry.insert(0, barcode)
            
            # Check if article exists
            if barcode in self.products:
                # Article exists - populate fields for update
                product = self.products[barcode]
                name_entry.delete(0, tk.END)
                name_entry.insert(0, product["name"])
                price_entry.delete(0, tk.END)
                price_entry.insert(0, str(product["price"]))
                stock_entry.delete(0, tk.END)
                stock_entry.insert(0, str(product.get("stock", 0)))
                
                status_label.config(text=f"Article '{product['name']}' trouvé. Modifier les détails ci-dessous.", 
                                    foreground="blue")
                details_frame.grid()  # Show details frame
                name_entry.focus_set()
            else:
                # New article - clear fields and try to fetch from API
                name_entry.delete(0, tk.END)
                price_entry.delete(0, tk.END)
                stock_entry.delete(0, tk.END)
                
                status_label.config(text=f"Recherche des informations pour '{barcode}'...", 
                                    foreground="orange")
                dialog.update()  # Update UI to show status
                
                # Try to fetch product info from Open Food Facts
                product_name = fetch_product_info(barcode)
                
                if product_name:
                    name_entry.insert(0, product_name)
                    status_label.config(text=f"Produit trouvé: '{product_name}'. Vérifier et compléter les détails.", 
                                        foreground="green")
                else:
                    status_label.config(text=f"Nouveau code-barres '{barcode}'. Entrer les détails ci-dessous.", 
                                        foreground="green")
                
                details_frame.grid()  # Show details frame
                name_entry.focus_set()
        
        def save_article():
            barcode = barcode_entry.get().strip()
            name = name_entry.get().strip()
            price_str = price_entry.get().strip()
            stock_str = stock_entry.get().strip()
            
            # Barcode has already been converted when scanned, so don't convert again
            # Validation
            if not barcode:
                messagebox.showerror("Érreur", "Veuillez entrer un code-barres")
                return
            
            if not name:
                messagebox.showerror("Érreur", "Veuillez entrer un nom de produit")
                return
            
            try:
                price = float(price_str)
                if price < 0:
                    raise ValueError("Le prix ne peut pas être négatif")
            except ValueError:
                messagebox.showerror("Érreur", "Veuillez entrer un prix valide")
                return
            
            try:
                stock = int(stock_str) if stock_str else 0
                if stock < 0:
                    raise ValueError("Le stock ne peut pas être négatif")
            except ValueError:
                messagebox.showerror("Érreur", "Veuillez entrer une quantité de stock valide")
                return
            
            # Save article
            self.products[barcode] = {
                "name": name,
                "price": price,
                "stock": stock
            }
            
            if self.save_products():
                messagebox.showinfo("Succ\u00e8s", f"Article '{name}' enregistr\u00e9 avec succ\u00e8s!\nCode-barres: {barcode}\nPrix: {price:.2f} \u20ac\nStock: {stock}")
                # Update low stock display
                self.update_low_stock_display()
            else:
                return  # Don't reset form if save failed
            
            # Reset form
            barcode_entry.delete(0, tk.END)
            name_entry.delete(0, tk.END)
            price_entry.delete(0, tk.END)
            stock_entry.delete(0, tk.END)
            details_frame.grid_remove()
            status_label.config(text="")
            barcode_entry.focus_set()
        
        # Bind Enter key to barcode entry
        barcode_entry.bind('<Return>', process_article_barcode)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Enregistrer Article", command=save_article).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Fermer", command=dialog.destroy).grid(row=0, column=1, padx=5)
    
    def show_stats_dialog(self):
        """Show dialog for statistics export with date filters"""
        from dateutil.relativedelta import relativedelta
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Exporter Statistiques")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Date filters
        filter_frame = ttk.LabelFrame(main_frame, text="P\u00e9riode", padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Calculate current month's first and last day
        today = datetime.now()
        first_day_current_month = today.replace(day=1)
        last_day_current_month = (today.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)
        
        ttk.Label(filter_frame, text="De (AAAA-MM-JJ):").grid(row=0, column=0, sticky=tk.W, pady=5)
        from_date = ttk.Entry(filter_frame)
        from_date.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        from_date.insert(0, first_day_current_month.strftime("%Y-%m-%d"))
        
        ttk.Label(filter_frame, text="\u00c0 (AAAA-MM-JJ):").grid(row=1, column=0, sticky=tk.W, pady=5)
        to_date = ttk.Entry(filter_frame)
        to_date.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        to_date.insert(0, last_day_current_month.strftime("%Y-%m-%d"))
        
        filter_frame.columnconfigure(1, weight=1)
        
        # Statistics display
        stats_frame = ttk.LabelFrame(main_frame, text="Statistiques", padding="10")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(1, weight=1)
        
        stats_text = tk.Text(stats_frame, height=15, width=60, font=('Inter', 10))
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=stats_text.yview)
        stats_text.configure(yscroll=stats_scrollbar.set)
        
        stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        def calculate_stats():
            from_str = from_date.get().strip()
            to_str = to_date.get().strip()
            
            stats_text.delete(1.0, tk.END)
            
            if not self.transactions_file.exists():
                stats_text.insert(tk.END, "Aucune transaction trouv\u00e9e.")
                return
            
            with open(self.transactions_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                total_transactions = 0
                total_amount = 0.0
                payment_methods = {}
                members_stats = {}
                
                for trans in reader:
                    if len(trans) == 5:
                        trans_date = trans[0].split(' ')[0]
                        if from_str <= trans_date <= to_str:
                            total_transactions += 1
                            amount = float(trans[3])
                            total_amount += amount
                            
                            # Payment method stats
                            payment = trans[4]
                            if payment not in payment_methods:
                                payment_methods[payment] = {'count': 0, 'amount': 0.0}
                            payment_methods[payment]['count'] += 1
                            payment_methods[payment]['amount'] += amount
                            
                            # Member stats
                            member = trans[1]
                            if member not in members_stats:
                                members_stats[member] = {'count': 0, 'amount': 0.0}
                            members_stats[member]['count'] += 1
                            members_stats[member]['amount'] += amount
                
                # Display statistics
                stats_text.insert(tk.END, f"P\u00e9riode: {from_str} au {to_str}\n\n")
                stats_text.insert(tk.END, f"=== R\u00c9SUM\u00c9 G\u00c9N\u00c9RAL ===\n")
                stats_text.insert(tk.END, f"Nombre de transactions: {total_transactions}\n")
                stats_text.insert(tk.END, f"Montant total: {total_amount:.2f} \u20ac\n")
                stats_text.insert(tk.END, f"Montant moyen: {(total_amount/total_transactions):.2f} \u20ac\n\n" if total_transactions > 0 else "\n")
                
                # Payment methods breakdown
                stats_text.insert(tk.END, f"=== PAR M\u00c9THODE DE PAIEMENT ===\n")
                for payment, data in sorted(payment_methods.items()):
                    percentage = (data['amount'] / total_amount * 100) if total_amount > 0 else 0
                    stats_text.insert(tk.END, f"{payment}: {data['count']} transactions - {data['amount']:.2f} \u20ac ({percentage:.1f}%)\n")
                
                # Top members
                stats_text.insert(tk.END, f"\n=== TOP 10 MEMBRES ===\n")
                top_members = sorted(members_stats.items(), key=lambda x: x[1]['amount'], reverse=True)[:10]
                for i, (member, data) in enumerate(top_members, 1):
                    stats_text.insert(tk.END, f"{i}. {member}: {data['count']} transactions - {data['amount']:.2f} \u20ac\n")
        
        def export_stats():
            from tkinter import filedialog
            
            from_str = from_date.get().strip()
            to_str = to_date.get().strip()
            export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"statistiques_{from_str}_to_{to_str}_{export_timestamp}.txt"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=default_filename,
                filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
            )
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(stats_text.get(1.0, tk.END))
                    messagebox.showinfo("Succ\u00e8s", f"Statistiques export\u00e9es vers {filename}")
                except Exception as e:
                    messagebox.showerror("\u00c9rreur", f"\u00c9chec de l'export: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="Calculer", command=calculate_stats).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Exporter", command=export_stats).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Fermer", command=dialog.destroy).grid(row=0, column=2, padx=5)
        
        # Auto-calculate on open
        calculate_stats()
    
    def show_extract_dialog(self):
        """Show dialog for extracting data with date filters"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Extraire les Données")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Date filters
        filter_frame = ttk.LabelFrame(main_frame, text="Filtre par Date", padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(filter_frame, text="De (AAAA-MM-JJ):").grid(row=0, column=0, sticky=tk.W, pady=5)
        from_date = ttk.Entry(filter_frame)
        from_date.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        from_date.insert(0, datetime.now().strftime("%Y-%m-01"))
        
        ttk.Label(filter_frame, text="À (AAAA-MM-JJ):").grid(row=1, column=0, sticky=tk.W, pady=5)
        to_date = ttk.Entry(filter_frame)
        to_date.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        filter_frame.columnconfigure(1, weight=1)
        
        # Results
        result_frame = ttk.LabelFrame(main_frame, text="Transactions Filtrées", padding="10")
        result_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(1, weight=1)
        
        columns = ('Date', 'Member', 'Product', 'Amount', 'Payment')
        result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            result_tree.heading(col, text=col)
            result_tree.column(col, width=90)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_tree.yview)
        result_tree.configure(yscroll=scrollbar.set)
        
        result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # Summary label
        summary_label = ttk.Label(main_frame, text="", font=('Inter', 10, 'bold'))
        summary_label.grid(row=2, column=0, pady=5)
        
        def apply_filter():
            # Clear existing items
            for item in result_tree.get_children():
                result_tree.delete(item)
            
            from_str = from_date.get().strip()
            to_str = to_date.get().strip()
            
            if self.transactions_file.exists():
                with open(self.transactions_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    
                    filtered = []
                    total_amount = 0.0
                    
                    for trans in reader:
                        if len(trans) == 5:
                            trans_date = trans[0].split(' ')[0]
                            if from_str <= trans_date <= to_str:
                                result_tree.insert('', tk.END, values=trans)
                                filtered.append(trans)
                                total_amount += float(trans[3])
                    
                    summary_label.config(text=f"Total: {len(filtered)} transactions - {total_amount:.2f} €")
        
        def export_csv():
            from tkinter import filedialog
            
            # Create default filename with filter dates and timestamp
            from_str = from_date.get().strip()
            to_str = to_date.get().strip()
            export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"transactions_{from_str}_to_{to_str}_{export_timestamp}.csv"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
            )
            if filename:
                with open(self.transactions_file, 'r', encoding='utf-8') as f_in:
                    reader = csv.reader(f_in)
                    header = next(reader)
                    
                    with open(filename, 'w', newline='', encoding='utf-8') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow(header)
                        
                        for trans in reader:
                            if len(trans) == 5:
                                trans_date = trans[0].split(' ')[0]
                                if from_str <= trans_date <= to_str:
                                    writer.writerow(trans)
                
                messagebox.showinfo("Succès", f"Données exportées vers {filename}")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=10)
        
        ttk.Button(button_frame, text="Appliquer Filtre", command=apply_filter).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Exporter CSV", command=export_csv).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Fermer", command=dialog.destroy).grid(row=0, column=2, padx=5)
        
        # Auto-apply filter
        apply_filter()
    
    def show_manage_barcodes_dialog(self):
        """Show dialog for managing member and payment method barcodes"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Gérer les Code-Barres")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0)
        
        # Title
        ttk.Label(main_frame, text="Gestion des Code-Barres", 
                  font=('Inter', 14, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Members tab
        members_frame = ttk.Frame(notebook, padding="10")
        notebook.add(members_frame, text="Membres")
        
        # Payment methods tab
        payments_frame = ttk.Frame(notebook, padding="10")
        notebook.add(payments_frame, text="Méthodes de Paiement")
        
        # === MEMBERS TAB ===
        ttk.Label(members_frame, text="Membres existants:", font=('Inter', 11, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Members listbox
        members_list_frame = ttk.Frame(members_frame)
        members_list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        members_listbox = tk.Listbox(members_list_frame, height=10, width=40, font=('Inter', 10))
        members_scrollbar = ttk.Scrollbar(members_list_frame, orient=tk.VERTICAL, command=members_listbox.yview)
        members_listbox.configure(yscroll=members_scrollbar.set)
        
        members_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        members_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Populate members
        for barcode, name in sorted(self.members.items(), key=lambda x: x[1]):
            members_listbox.insert(tk.END, f"{name} ({barcode})")
        
        # Member actions
        member_action_frame = ttk.Frame(members_frame)
        member_action_frame.grid(row=2, column=0, pady=10)
        
        ttk.Label(member_action_frame, text="Nouveau membre:").grid(row=0, column=0, sticky=tk.W, pady=5)
        new_member_name = ttk.Entry(member_action_frame, font=('Inter', 11), width=25)
        new_member_name.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(member_action_frame, text="Scanner code-barres:").grid(row=1, column=0, sticky=tk.W, pady=5)
        member_barcode_entry = ttk.Entry(member_action_frame, font=('Inter', 11), width=25)
        member_barcode_entry.grid(row=1, column=1, padx=5, pady=5)
        
        member_status = ttk.Label(member_action_frame, text="", font=('Inter', 9), foreground='blue')
        member_status.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Store the old barcode for editing
        editing_member = {'old_barcode': None}
        
        def on_member_select(event):
            """When a member is selected from the list, populate the fields for editing"""
            selection = members_listbox.curselection()
            if not selection:
                return
            
            item_text = members_listbox.get(selection[0])
            # Extract name and barcode from "Name (barcode)" format
            parts = item_text.rsplit(' (', 1)
            name = parts[0]
            barcode = parts[1].rstrip(')')
            
            # Populate fields
            new_member_name.delete(0, tk.END)
            new_member_name.insert(0, name)
            member_barcode_entry.delete(0, tk.END)
            member_barcode_entry.insert(0, barcode)
            
            # Store old barcode for editing
            editing_member['old_barcode'] = barcode
            
            member_status.config(text=f"Édition de '{name}'. Scanner un nouveau code-barres ou modifier le nom.", foreground='blue')
            member_barcode_entry.focus_set()
        
        members_listbox.bind('<<ListboxSelect>>', on_member_select)
        
        def add_or_update_member(event=None):
            barcode = member_barcode_entry.get().strip()
            name = new_member_name.get().strip()
            
            if not barcode or not name:
                member_status.config(text="Veuillez entrer un nom et scanner un code-barres", foreground='red')
                return
            
            # Convert AZERTY if enabled
            if AZERTY_CONVERT:
                original_barcode = barcode
                barcode = qwerty_to_azerty(barcode)
                if barcode != original_barcode:
                    member_barcode_entry.delete(0, tk.END)
                    member_barcode_entry.insert(0, barcode)
            
            old_barcode = editing_member['old_barcode']
            
            # If editing an existing member
            if old_barcode and old_barcode in self.members:
                # If barcode changed, check if new barcode already exists
                if barcode != old_barcode and barcode in self.members:
                    messagebox.showerror("Erreur", f"Le code-barres {barcode} est déjà utilisé par '{self.members[barcode]}'")
                    return
                
                # Remove old entry if barcode changed
                if barcode != old_barcode:
                    del self.members[old_barcode]
                
                # Update or add with new barcode
                self.members[barcode] = name
                self.save_members()
                member_status.config(text=f"Membre mis à jour: {name}", foreground='green')
                
                # Refresh list
                members_listbox.delete(0, tk.END)
                for bc, n in sorted(self.members.items(), key=lambda x: x[1]):
                    members_listbox.insert(tk.END, f"{n} ({bc})")
            else:
                # Adding new member - check if barcode exists
                if barcode in self.members:
                    old_name = self.members[barcode]
                    if messagebox.askyesno("Confirmation", f"Le code-barres existe déjà pour '{old_name}'.\\n\\nRemplacer par '{name}' ?"):
                        self.members[barcode] = name
                        self.save_members()
                        member_status.config(text=f"Membre mis à jour: {name}", foreground='green')
                        # Refresh list
                        members_listbox.delete(0, tk.END)
                        for bc, n in sorted(self.members.items(), key=lambda x: x[1]):
                            members_listbox.insert(tk.END, f"{n} ({bc})")
                    else:
                        return
                else:
                    self.members[barcode] = name
                    self.save_members()
                    member_status.config(text=f"Membre ajouté: {name}", foreground='green')
                    members_listbox.insert(tk.END, f"{name} ({barcode})")
            
            # Clear inputs and editing state
            new_member_name.delete(0, tk.END)
            member_barcode_entry.delete(0, tk.END)
            editing_member['old_barcode'] = None
            new_member_name.focus_set()
        
        def delete_selected_member():
            selection = members_listbox.curselection()
            if not selection:
                messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un membre à supprimer")
                return
            
            item_text = members_listbox.get(selection[0])
            # Extract barcode from "Name (barcode)" format
            barcode = item_text.split('(')[-1].rstrip(')')
            name = self.members.get(barcode, "")
            
            if messagebox.askyesno("Confirmation", f"Supprimer le membre '{name}' ?"):
                del self.members[barcode]
                self.save_members()
                members_listbox.delete(selection[0])
                member_status.config(text=f"Membre supprimé: {name}", foreground='orange')
        
        member_barcode_entry.bind('<Return>', add_or_update_member)
        
        member_button_frame = ttk.Frame(members_frame)
        member_button_frame.grid(row=3, column=0, pady=10)
        ttk.Button(member_button_frame, text="Ajouter/Modifier", command=add_or_update_member).grid(row=0, column=0, padx=5)
        ttk.Button(member_button_frame, text="Supprimer Sélection", command=delete_selected_member).grid(row=0, column=1, padx=5)
        
        # === PAYMENT METHODS TAB ===
        ttk.Label(payments_frame, text="Méthodes de paiement:", font=('Inter', 11, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Payments listbox
        payments_list_frame = ttk.Frame(payments_frame)
        payments_list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        payments_listbox = tk.Listbox(payments_list_frame, height=10, width=40, font=('Inter', 10))
        payments_scrollbar = ttk.Scrollbar(payments_list_frame, orient=tk.VERTICAL, command=payments_listbox.yview)
        payments_listbox.configure(yscroll=payments_scrollbar.set)
        
        payments_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        payments_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Populate payments
        for barcode, name in sorted(self.payment_methods.items(), key=lambda x: x[1]):
            payments_listbox.insert(tk.END, f"{name} ({barcode})")
        
        # Payment actions
        payment_action_frame = ttk.Frame(payments_frame)
        payment_action_frame.grid(row=2, column=0, pady=10)
        
        ttk.Label(payment_action_frame, text="Nouvelle méthode:").grid(row=0, column=0, sticky=tk.W, pady=5)
        new_payment_name = ttk.Entry(payment_action_frame, font=('Inter', 11), width=25)
        new_payment_name.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(payment_action_frame, text="Scanner code-barres:").grid(row=1, column=0, sticky=tk.W, pady=5)
        payment_barcode_entry = ttk.Entry(payment_action_frame, font=('Inter', 11), width=25)
        payment_barcode_entry.grid(row=1, column=1, padx=5, pady=5)
        
        payment_status = ttk.Label(payment_action_frame, text="", font=('Inter', 9), foreground='blue')
        payment_status.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Store the old barcode for editing
        editing_payment = {'old_barcode': None}
        
        def on_payment_select(event):
            """When a payment method is selected from the list, populate the fields for editing"""
            selection = payments_listbox.curselection()
            if not selection:
                return
            
            item_text = payments_listbox.get(selection[0])
            # Extract name and barcode from "Name (barcode)" format
            parts = item_text.rsplit(' (', 1)
            name = parts[0]
            barcode = parts[1].rstrip(')')
            
            # Populate fields
            new_payment_name.delete(0, tk.END)
            new_payment_name.insert(0, name)
            payment_barcode_entry.delete(0, tk.END)
            payment_barcode_entry.insert(0, barcode)
            
            # Store old barcode for editing
            editing_payment['old_barcode'] = barcode
            
            payment_status.config(text=f"Édition de '{name}'. Scanner un nouveau code-barres ou modifier le nom.", foreground='blue')
            payment_barcode_entry.focus_set()
        
        payments_listbox.bind('<<ListboxSelect>>', on_payment_select)
        
        def add_or_update_payment(event=None):
            barcode = payment_barcode_entry.get().strip()
            name = new_payment_name.get().strip()
            
            if not barcode or not name:
                payment_status.config(text="Veuillez entrer un nom et scanner un code-barres", foreground='red')
                return
            
            # Convert AZERTY if enabled
            if AZERTY_CONVERT:
                original_barcode = barcode
                barcode = qwerty_to_azerty(barcode)
                if barcode != original_barcode:
                    payment_barcode_entry.delete(0, tk.END)
                    payment_barcode_entry.insert(0, barcode)
            
            old_barcode = editing_payment['old_barcode']
            
            # If editing an existing payment method
            if old_barcode and old_barcode in self.payment_methods:
                # If barcode changed, check if new barcode already exists
                if barcode != old_barcode and barcode in self.payment_methods:
                    messagebox.showerror("Erreur", f"Le code-barres {barcode} est déjà utilisé par '{self.payment_methods[barcode]}'")
                    return
                
                # Remove old entry if barcode changed
                if barcode != old_barcode:
                    del self.payment_methods[old_barcode]
                
                # Update or add with new barcode
                self.payment_methods[barcode] = name
                self.save_payment_methods()
                payment_status.config(text=f"Méthode mise à jour: {name}", foreground='green')
                
                # Refresh list
                payments_listbox.delete(0, tk.END)
                for bc, n in sorted(self.payment_methods.items(), key=lambda x: x[1]):
                    payments_listbox.insert(tk.END, f"{n} ({bc})")
            else:
                # Adding new payment method - check if barcode exists
                if barcode in self.payment_methods:
                    old_name = self.payment_methods[barcode]
                    if messagebox.askyesno("Confirmation", f"Le code-barres existe déjà pour '{old_name}'.\\n\\nRemplacer par '{name}' ?"):
                        self.payment_methods[barcode] = name
                        self.save_payment_methods()
                        payment_status.config(text=f"Méthode mise à jour: {name}", foreground='green')
                        # Refresh list
                        payments_listbox.delete(0, tk.END)
                        for bc, n in sorted(self.payment_methods.items(), key=lambda x: x[1]):
                            payments_listbox.insert(tk.END, f"{n} ({bc})")
                    else:
                        return
                else:
                    self.payment_methods[barcode] = name
                    self.save_payment_methods()
                    payment_status.config(text=f"Méthode ajoutée: {name}", foreground='green')
                    payments_listbox.insert(tk.END, f"{name} ({barcode})")
            
            # Clear inputs and editing state
            new_payment_name.delete(0, tk.END)
            payment_barcode_entry.delete(0, tk.END)
            editing_payment['old_barcode'] = None
            new_payment_name.focus_set()
        
        def delete_selected_payment():
            selection = payments_listbox.curselection()
            if not selection:
                messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une méthode à supprimer")
                return
            
            item_text = payments_listbox.get(selection[0])
            # Extract barcode from "Name (barcode)" format
            barcode = item_text.split('(')[-1].rstrip(')')
            name = self.payment_methods.get(barcode, "")
            
            if messagebox.askyesno("Confirmation", f"Supprimer la méthode '{name}' ?"):
                del self.payment_methods[barcode]
                self.save_payment_methods()
                payments_listbox.delete(selection[0])
                payment_status.config(text=f"Méthode supprimée: {name}", foreground='orange')
        
        payment_barcode_entry.bind('<Return>', add_or_update_payment)
        
        payment_button_frame = ttk.Frame(payments_frame)
        payment_button_frame.grid(row=3, column=0, pady=10)
        ttk.Button(payment_button_frame, text="Ajouter/Modifier", command=add_or_update_payment).grid(row=0, column=0, padx=5)
        ttk.Button(payment_button_frame, text="Supprimer Sélection", command=delete_selected_payment).grid(row=0, column=1, padx=5)
        
        # Close button
        ttk.Button(main_frame, text="Fermer", command=dialog.destroy).grid(row=2, column=0, columnspan=2, pady=(20, 0))
    
    def save_members(self):
        """Save members to JSON file"""
        try:
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(self.members, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'enregistrement des membres: {str(e)}")
            return False
    
    def save_payment_methods(self):
        """Save payment methods to JSON file"""
        try:
            with open(self.payment_methods_file, 'w', encoding='utf-8') as f:
                json.dump(self.payment_methods, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'enregistrement des méthodes de paiement: {str(e)}")
            return False


def main():
    root = tk.Tk()
    app = StockManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
