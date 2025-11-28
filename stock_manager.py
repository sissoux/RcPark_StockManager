"""
Stock Manager Application for Association
Barcode-based beverage stock management system
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import csv
import os
from pathlib import Path


class StockManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Manager - Association")
        self.root.geometry("800x600")
        
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
        self.current_product = None
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
        """Load JSON file or return default if doesn't exist"""
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Stock Manager", font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Barcode input (hidden)
        barcode_frame = ttk.LabelFrame(main_frame, text="Scan Barcode", padding="10")
        barcode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.barcode_entry = ttk.Entry(barcode_frame, font=('Arial', 14))
        self.barcode_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.barcode_entry.bind('<Return>', self.process_barcode)
        barcode_frame.columnconfigure(0, weight=1)
        
        # Current order status
        status_frame = ttk.LabelFrame(main_frame, text="Current Order", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(status_frame, text="Member:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.member_label = ttk.Label(status_frame, text="---", font=('Arial', 12, 'bold'), foreground='blue')
        self.member_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        
        ttk.Label(status_frame, text="Product:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.product_label = ttk.Label(status_frame, text="---", font=('Arial', 12, 'bold'), foreground='green')
        self.product_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=2)
        
        ttk.Label(status_frame, text="Amount:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.amount_label = ttk.Label(status_frame, text="0.00 €", font=('Arial', 14, 'bold'), foreground='red')
        self.amount_label.grid(row=2, column=1, sticky=tk.W, padx=10, pady=2)
        
        # Recent transactions
        trans_frame = ttk.LabelFrame(main_frame, text="Last 5 Transactions", padding="10")
        trans_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(3, weight=1)
        
        # Treeview for transactions
        columns = ('Time', 'Member', 'Product', 'Amount', 'Payment')
        self.trans_tree = ttk.Treeview(trans_frame, columns=columns, show='headings', height=5)
        
        self.trans_tree.heading('Time', text='Time')
        self.trans_tree.heading('Member', text='Member')
        self.trans_tree.heading('Product', text='Product')
        self.trans_tree.heading('Amount', text='Amount')
        self.trans_tree.heading('Payment', text='Payment')
        
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
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Extract Data", command=self.show_extract_dialog).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Reset Order", command=self.reset_order).grid(row=0, column=1, padx=5)
        
        # Load recent transactions
        self.load_recent_transactions()
    
    def process_barcode(self, event=None):
        """Process scanned barcode"""
        barcode = self.barcode_entry.get().strip()
        self.barcode_entry.delete(0, tk.END)
        
        if not barcode:
            return
        
        # Check if it's a member
        if barcode in self.members:
            self.current_member = self.members[barcode]
            self.member_label.config(text=self.current_member)
            self.show_status(f"Member: {self.current_member}", "info")
            return
        
        # Check if it's a product
        if barcode in self.products:
            if not self.current_member:
                self.show_status("Please scan member barcode first!", "warning")
                return
            
            self.current_product = self.products[barcode]["name"]
            self.current_amount = self.products[barcode]["price"]
            self.product_label.config(text=self.current_product)
            self.amount_label.config(text=f"{self.current_amount:.2f} €")
            self.show_status(f"Product: {self.current_product} - {self.current_amount:.2f} €", "info")
            return
        
        # Check if it's a payment method
        if barcode in self.payment_methods:
            if not self.current_member or not self.current_product:
                self.show_status("Please scan member and product first!", "warning")
                return
            
            payment_method = self.payment_methods[barcode]
            self.save_transaction(payment_method)
            self.show_status(f"Transaction saved! Payment: {payment_method}", "success")
            self.reset_order()
            return
        
        # Unknown barcode
        self.show_status(f"Unknown barcode: {barcode}", "error")
    
    def save_transaction(self, payment_method):
        """Save transaction to CSV file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.transactions_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                self.current_member,
                self.current_product,
                f"{self.current_amount:.2f}",
                payment_method
            ])
        
        # Reload recent transactions
        self.load_recent_transactions()
    
    def reset_order(self):
        """Reset current order"""
        self.current_member = None
        self.current_product = None
        self.current_amount = 0.0
        
        self.member_label.config(text="---")
        self.product_label.config(text="---")
        self.amount_label.config(text="0.00 €")
        
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
                    time_only = trans[0].split(' ')[1] if ' ' in trans[0] else trans[0]
                    self.trans_tree.insert('', tk.END, values=(time_only, trans[1], trans[2], trans[3] + ' €', trans[4]))
    
    def show_status(self, message, status_type):
        """Show status message in the root window title"""
        if status_type == "success":
            color = "green"
        elif status_type == "warning":
            color = "orange"
        elif status_type == "error":
            color = "red"
        else:
            color = "blue"
        
        # Update window title temporarily
        original_title = self.root.title()
        self.root.title(f"Stock Manager - {message}")
        self.root.after(2000, lambda: self.root.title(original_title))
    
    def show_extract_dialog(self):
        """Show dialog for extracting data with date filters"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Extract Data")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Date filters
        filter_frame = ttk.LabelFrame(main_frame, text="Date Filter", padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(filter_frame, text="From (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, pady=5)
        from_date = ttk.Entry(filter_frame)
        from_date.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        from_date.insert(0, datetime.now().strftime("%Y-%m-01"))
        
        ttk.Label(filter_frame, text="To (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W, pady=5)
        to_date = ttk.Entry(filter_frame)
        to_date.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        filter_frame.columnconfigure(1, weight=1)
        
        # Results
        result_frame = ttk.LabelFrame(main_frame, text="Filtered Transactions", padding="10")
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
        summary_label = ttk.Label(main_frame, text="", font=('Arial', 10, 'bold'))
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
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if filename:
                from_str = from_date.get().strip()
                to_str = to_date.get().strip()
                
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
                
                messagebox.showinfo("Success", f"Data exported to {filename}")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=10)
        
        ttk.Button(button_frame, text="Apply Filter", command=apply_filter).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Export CSV", command=export_csv).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).grid(row=0, column=2, padx=5)
        
        # Auto-apply filter
        apply_filter()


def main():
    root = tk.Tk()
    app = StockManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
