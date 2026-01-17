#!/usr/bin/env python3
"""Invoice Processor - Main GUI Application."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from pathlib import Path
from ..parsers.pdf_parser import parse_invoice
from ..utils.file_manager import FileManager


class InvoiceProcessorApp:
    """Main application window for invoice processing."""

    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Invoice Processor")
        self.root.geometry("1200x600")

        # File manager
        self.file_manager = FileManager()

        # Invoice data: filename -> {data, transfer_type_var, payment_set_var}
        self.invoices = {}

        # Background scanning
        self.scanning = True
        self.scan_thread = None

        # Create UI
        self.create_ui()

        # Initial load
        self.initial_load()

        # Start background scanning
        self.start_background_scan()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_ui(self):
        """Create the user interface."""
        # Top frame with refresh button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Invoice Processor",
                  font=('Helvetica', 16, 'bold')).pack(side=tk.LEFT)

        self.refresh_btn = ttk.Button(top_frame, text="Refresh",
                                       command=self.manual_refresh)
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)

        # Progress bar
        self.progress_frame = ttk.Frame(self.root, padding="10")
        self.progress_frame.pack(fill=tk.X)

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Hide progress initially
        self.progress_frame.pack_forget()

        # Table frame
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview with scrollbars
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(table_frame,
                                  columns=('filename', 'from', 'to', 'amount',
                                          'currency', 'banking', 'transfer', 'payment', 'saved'),
                                  show='headings',
                                  yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Define columns
        self.tree.heading('filename', text='Filename')
        self.tree.heading('from', text='From')
        self.tree.heading('to', text='To')
        self.tree.heading('amount', text='Amount')
        self.tree.heading('currency', text='Currency')
        self.tree.heading('banking', text='Banking')
        self.tree.heading('transfer', text='Transfer Type')
        self.tree.heading('payment', text='Payment Set')
        self.tree.heading('saved', text='Invoice Saved')

        # Column widths
        self.tree.column('filename', width=140)
        self.tree.column('from', width=130)
        self.tree.column('to', width=130)
        self.tree.column('amount', width=80)
        self.tree.column('currency', width=60)
        self.tree.column('banking', width=150)
        self.tree.column('transfer', width=90)
        self.tree.column('payment', width=90)
        self.tree.column('saved', width=80)

        # Pack table and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Bind click events for checkboxes
        self.tree.bind('<Button-1>', self.on_tree_click)
        # Bind double-click for detail view
        self.tree.bind('<Double-Button-1>', self.show_detail_view)

        # Status bar
        status_frame = ttk.Frame(self.root, padding="5")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)

    def initial_load(self):
        """Load all invoices from pending folder with progress bar."""
        # Scan for files
        files = self.file_manager.scan_folder(initial_scan=True)

        if not files:
            self.status_label.config(text="No invoices found in pending folder")
            return

        # Show progress bar
        self.progress_frame.pack(fill=tk.X, after=self.root.children['!frame'])
        self.progress_bar['maximum'] = len(files)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Loading invoices...")

        # Load each file
        for i, filename in enumerate(files):
            self.progress_bar['value'] = i + 1
            self.progress_label.config(text=f"Loading {i+1}/{len(files)}: {filename}")
            self.root.update_idletasks()

            self.load_invoice(filename)

            # Small delay to show progress
            time.sleep(0.05)

        # Hide progress bar
        self.progress_frame.pack_forget()
        self.status_label.config(text=f"Loaded {len(files)} invoices")

    def load_invoice(self, filename: str):
        """
        Load and parse an invoice file.

        Args:
            filename: Name of the PDF file to load
        """
        try:
            # Parse the PDF
            filepath = self.file_manager.get_full_path(filename)
            data = parse_invoice(str(filepath))

            # Create checkbox variables
            transfer_var = tk.BooleanVar(value=False)
            payment_var = tk.BooleanVar(value=False)

            # Determine transfer type based on currency
            transfer_type = "Local" if data['currency'] == "EUR" else "International"

            # Format banking info for display
            banking_display = self.format_banking_info(data)

            # Store invoice data
            self.invoices[filename] = {
                'data': data,
                'transfer_var': transfer_var,
                'payment_var': payment_var,
                'transfer_type': transfer_type
            }

            # Add to tree
            self.tree.insert('', 'end', iid=filename, values=(
                filename,
                data['sender'],
                data['recipient'],
                data['amount'],
                data['currency'],
                banking_display,
                '☐',  # Transfer checkbox
                '☐',  # Payment checkbox
                'No'
            ))

            # Watch for checkbox changes
            transfer_var.trace_add('write', lambda *args, f=filename: self.on_checkbox_changed(f))
            payment_var.trace_add('write', lambda *args, f=filename: self.on_checkbox_changed(f))

        except Exception as e:
            print(f"Error loading invoice {filename}: {e}")
            # Still add to table but with error info
            self.tree.insert('', 'end', iid=filename, values=(
                filename,
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                '☐',
                '☐',
                'No'
            ))

    def format_banking_info(self, data: dict) -> str:
        """Format banking information for display in table."""
        if data.get('iban') and data['iban'] != "PARSING FAILED":
            # Show abbreviated IBAN
            iban = data['iban']
            return f"IBAN: {iban[:4]}...{iban[-4:]}"
        elif data.get('bank_name') and data['bank_name'] != "PARSING FAILED":
            # Show bank name (truncated)
            bank = data['bank_name']
            return f"Bank: {bank[:20]}..." if len(bank) > 20 else f"Bank: {bank}"
        elif data.get('payment_address') and data['payment_address'] != "PARSING FAILED":
            return "Payment Address"
        else:
            return "PARSING FAILED"

    def show_detail_view(self, event):
        """Show detailed invoice information in a popup window."""
        # Get selected item
        selection = self.tree.selection()
        if not selection:
            return

        filename = selection[0]
        if filename not in self.invoices:
            return

        data = self.invoices[filename]['data']

        # Create popup window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Invoice Details - {filename}")
        detail_window.geometry("600x500")

        # Create scrollable text widget
        text_frame = ttk.Frame(detail_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(text_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scroll.set,
                             font=('Courier', 10))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=text_widget.yview)

        # Build detailed info
        details = f"""INVOICE DETAILS: {filename}
{'-' * 60}

FROM (SENDER):
  Name: {data.get('sender', 'N/A')}
  Address: {data.get('sender_address', 'N/A')}
  Email: {data.get('sender_email', 'N/A')}

TO (RECIPIENT):
  Name: {data.get('recipient', 'N/A')}
  Address: {data.get('recipient_address', 'N/A')}
  Email: {data.get('recipient_email', 'N/A')}

PAYMENT INFORMATION:
  Amount: {data.get('amount', 'N/A')}
  Currency: {data.get('currency', 'N/A')}
  Transfer Type: {self.invoices[filename]['transfer_type']}

BANKING DETAILS:
  Bank Name: {data.get('bank_name', 'N/A')}
  IBAN: {data.get('iban', 'N/A')}
  BIC/SWIFT: {data.get('bic', 'N/A')}
  Payment Address: {data.get('payment_address', 'N/A')}

{'-' * 60}
Double-click to close this window.
"""

        text_widget.insert('1.0', details)
        text_widget.config(state='disabled')  # Make read-only

        # Close on double-click
        detail_window.bind('<Double-Button-1>', lambda e: detail_window.destroy())

    def on_tree_click(self, event):
        """Handle clicks on the tree (for checkbox toggles)."""
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return

        column = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)

        if not row or row not in self.invoices:
            return

        # Column #7 is Transfer Type, #8 is Payment Set (after adding Banking column)
        if column == '#7':
            # Toggle transfer type checkbox
            var = self.invoices[row]['transfer_var']
            var.set(not var.get())
        elif column == '#8':
            # Toggle payment set checkbox
            var = self.invoices[row]['payment_var']
            var.set(not var.get())

    def on_checkbox_changed(self, filename):
        """
        Handle checkbox state changes.

        Args:
            filename: The invoice filename whose checkbox changed
        """
        if filename not in self.invoices:
            return

        invoice = self.invoices[filename]
        transfer_checked = invoice['transfer_var'].get()
        payment_checked = invoice['payment_var'].get()

        # Update display
        transfer_symbol = '☑' if transfer_checked else '☐'
        payment_symbol = '☑' if payment_checked else '☐'

        # Check if both are checked
        if transfer_checked and payment_checked:
            saved_status = 'Yes'
        else:
            saved_status = 'No'

        # Update tree
        current_values = self.tree.item(filename, 'values')
        self.tree.item(filename, values=(
            current_values[0],  # filename
            current_values[1],  # from
            current_values[2],  # to
            current_values[3],  # amount
            current_values[4],  # currency
            current_values[5],  # banking
            transfer_symbol,
            payment_symbol,
            saved_status
        ))

        # If both checked, move file and remove from display
        if transfer_checked and payment_checked:
            # Move file in a separate thread to avoid blocking UI
            threading.Thread(target=self.process_invoice, args=(filename,),
                           daemon=True).start()

    def process_invoice(self, filename):
        """
        Process an invoice (move to processed folder and remove from table).

        Args:
            filename: The invoice filename to process
        """
        try:
            # Move the file
            success = self.file_manager.move_invoice(filename)

            if success:
                # Update UI in main thread
                self.root.after(0, self.remove_invoice_from_table, filename)
                self.root.after(0, self.status_label.config,
                              {'text': f"Processed: {filename}"})
            else:
                self.root.after(0, self.status_label.config,
                              {'text': f"Error processing: {filename}"})

        except Exception as e:
            print(f"Error processing invoice {filename}: {e}")
            self.root.after(0, self.status_label.config,
                          {'text': f"Error: {e}"})

    def remove_invoice_from_table(self, filename):
        """
        Remove an invoice from the table.

        Args:
            filename: The invoice filename to remove
        """
        try:
            if self.tree.exists(filename):
                self.tree.delete(filename)
            if filename in self.invoices:
                del self.invoices[filename]
        except Exception as e:
            print(f"Error removing invoice from table: {e}")

    def manual_refresh(self):
        """Manually refresh the invoice list."""
        self.status_label.config(text="Refreshing...")
        self.refresh_btn.config(state='disabled')

        # Scan for new files
        new_files = self.file_manager.scan_folder(initial_scan=False)

        if new_files:
            for filename in new_files:
                self.load_invoice(filename)
            self.status_label.config(text=f"Added {len(new_files)} new invoice(s)")
        else:
            self.status_label.config(text="No new invoices found")

        self.refresh_btn.config(state='normal')

    def background_scan_loop(self):
        """Background thread that scans for new files every 30 seconds."""
        while self.scanning:
            # Wait 30 seconds
            for _ in range(300):  # 30 seconds = 300 * 0.1s
                if not self.scanning:
                    return
                time.sleep(0.1)

            # Scan for new files
            try:
                new_files = self.file_manager.scan_folder(initial_scan=False)

                if new_files:
                    # Update UI in main thread
                    for filename in new_files:
                        self.root.after(0, self.load_invoice, filename)
                    self.root.after(0, self.status_label.config,
                                  {'text': f"Auto-scan: Found {len(new_files)} new invoice(s)"})
            except Exception as e:
                print(f"Error in background scan: {e}")

    def start_background_scan(self):
        """Start the background scanning thread."""
        self.scan_thread = threading.Thread(target=self.background_scan_loop,
                                           daemon=True)
        self.scan_thread.start()

    def on_closing(self):
        """Handle window close event."""
        self.scanning = False
        if self.scan_thread and self.scan_thread.is_alive():
            # Give thread time to exit
            time.sleep(0.2)
        self.root.destroy()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = InvoiceProcessorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
