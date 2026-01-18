#!/usr/bin/env python3
"""Invoice Processor - Main GUI Application."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import subprocess
import platform
from pathlib import Path
from ..parsers.pdf_parser import parse_invoice
from ..utils.file_manager import FileManager
from ..utils.vehicle_matcher import VehicleMatcher
from ..core.config import get_config
from ..core.logging_config import get_logger

logger = get_logger(__name__)


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

        # Vehicle matcher
        self.vehicle_matcher = None
        self._init_vehicle_matcher()

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

    def _init_vehicle_matcher(self):
        """Initialize vehicle matcher if enabled in config."""
        try:
            config = get_config()
            if config.vehicle_matching.enabled:
                self.vehicle_matcher = VehicleMatcher(
                    excel_path=config.vehicle_matching.excel_path,
                    threshold=config.vehicle_matching.threshold
                )
                logger.info("Vehicle matcher initialized")
            else:
                logger.info("Vehicle matching disabled in config")
        except Exception as e:
            logger.warning(f"Vehicle matcher initialization failed: {e}")
            self.vehicle_matcher = None

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
                                  columns=('filename', 'from', 'to', 'vehicle_id', 'amount',
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
        self.tree.heading('vehicle_id', text='Vehicle ID')
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
        self.tree.column('vehicle_id', width=100)
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

        # Bind click events for checkboxes and filename opening
        self.tree.bind('<Button-1>', self.on_tree_click)
        # Bind double-click for detail view
        self.tree.bind('<Double-Button-1>', self.show_detail_view)
        # Bind mouse motion for cursor changes on filename column
        self.tree.bind('<Motion>', self.on_tree_motion)

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

            # Fuzzy match vehicle
            if self.vehicle_matcher and data['recipient'] != "PARSING FAILED":
                matched_name, vehicle_id, score = self.vehicle_matcher.match_recipient(
                    data['recipient']
                )
                data['original_recipient'] = data['recipient']
                data['vehicle_match_score'] = f"{score:.2f}"

                if score >= self.vehicle_matcher.threshold:
                    data['recipient'] = matched_name
                    data['vehicle_id'] = vehicle_id
                else:
                    data['vehicle_id'] = "N/A"
            else:
                data['vehicle_id'] = "N/A"

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
                data['vehicle_id'],
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
                "N/A",  # vehicle_id
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
        """Show detailed invoice information in a popup window with click-to-copy banking details."""
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
        detail_window.geometry("650x550")

        # Main frame with padding
        main_frame = ttk.Frame(detail_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instruction label
        instruction = ttk.Label(main_frame,
                               text="Click any banking detail to copy it to clipboard",
                               font=('Helvetica', 9, 'italic'),
                               foreground='#666')
        instruction.pack(pady=(0, 10))

        # Create scrollable frame
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Enable mouse wheel scrolling - platform-specific handling
        def on_mousewheel(event):
            # macOS and Windows have different event.delta values
            if platform.system() == 'Darwin':  # macOS
                canvas.yview_scroll(-1 * event.delta, "units")
            else:  # Windows
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind mouse wheel events
        canvas.bind_all("<MouseWheel>", on_mousewheel)  # Windows/macOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux scroll up
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux scroll down

        # Unbind when window closes to prevent conflicts
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            detail_window.destroy()

        # Header
        header = ttk.Label(scrollable_frame, text=f"INVOICE: {filename}",
                          font=('Helvetica', 12, 'bold'))
        header.pack(pady=(0, 10))

        # Helper function to create clickable fields
        def create_clickable_field(parent, label, value, is_banking=False, copy_value=None):
            """Create a field with click-to-copy functionality.

            Args:
                parent: Parent widget
                label: Field label
                value: Display value
                is_banking: Whether this is a banking field (clickable)
                copy_value: Value to copy (if different from display value)
            """
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)

            label_widget = ttk.Label(frame, text=f"{label}:", width=18, anchor='w')
            label_widget.pack(side=tk.LEFT)

            # Create value label
            value_label = ttk.Label(frame, text=value, anchor='w')
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Make banking fields clickable
            if is_banking and value != 'N/A' and value != 'PARSING FAILED':
                value_label.config(foreground='#0066cc', cursor='hand2')

                # Use copy_value if provided, otherwise use display value
                actual_copy_value = copy_value if copy_value is not None else value

                # Capture the original font ONCE at field creation time
                original_font = value_label.cget('font')

                def copy_to_clipboard(e):
                    detail_window.clipboard_clear()
                    detail_window.clipboard_append(actual_copy_value)
                    detail_window.update()
                    # Visual feedback
                    original_text = value_label.cget('text')
                    value_label.config(text='✓ Copied!', foreground='#00aa00')
                    detail_window.after(1000, lambda: value_label.config(
                        text=original_text, foreground='#0066cc', font=original_font))

                def on_enter(e):
                    # Add underline to the original font
                    if isinstance(original_font, str):
                        value_label.config(font=(original_font, 9, 'underline'))
                    elif isinstance(original_font, tuple):
                        value_label.config(font=(original_font[0] if len(original_font) > 0 else 'TkDefaultFont',
                                                 original_font[1] if len(original_font) > 1 else 9,
                                                 'underline'))
                    else:
                        value_label.config(font=('TkDefaultFont', 9, 'underline'))

                def on_leave(e):
                    # Restore to the captured original font
                    value_label.config(font=original_font)

                value_label.bind('<Button-1>', copy_to_clipboard)
                value_label.bind('<Enter>', on_enter)
                value_label.bind('<Leave>', on_leave)

            return frame

        # Sender section
        sender_frame = ttk.LabelFrame(scrollable_frame, text="FROM (SENDER)", padding="10")
        sender_frame.pack(fill=tk.X, pady=5)
        create_clickable_field(sender_frame, "Name", data.get('sender', 'N/A'))
        create_clickable_field(sender_frame, "Address", data.get('sender_address', 'N/A'))
        create_clickable_field(sender_frame, "Email", data.get('sender_email', 'N/A'))

        # Recipient section
        recipient_frame = ttk.LabelFrame(scrollable_frame, text="TO (RECIPIENT)", padding="10")
        recipient_frame.pack(fill=tk.X, pady=5)
        create_clickable_field(recipient_frame, "Name", data.get('recipient', 'N/A'))
        create_clickable_field(recipient_frame, "Vehicle ID", data.get('vehicle_id', 'N/A'))

        # Show original recipient name if it was replaced by vehicle matching
        if (data.get('original_recipient') and
            data.get('original_recipient') != 'PARSING FAILED' and
            data.get('original_recipient') != data.get('recipient')):
            create_clickable_field(recipient_frame, "Original Name", data.get('original_recipient'))
            create_clickable_field(recipient_frame, "Match Score", data.get('vehicle_match_score', '0.0'))

        create_clickable_field(recipient_frame, "Address", data.get('recipient_address', 'N/A'))
        create_clickable_field(recipient_frame, "Email", data.get('recipient_email', 'N/A'))

        # Payment section
        payment_frame = ttk.LabelFrame(scrollable_frame, text="PAYMENT INFORMATION", padding="10")
        payment_frame.pack(fill=tk.X, pady=5)

        # Format amount for display but keep raw value for copying
        raw_amount = data.get('amount', 'N/A')
        display_amount = raw_amount
        copy_amount = raw_amount

        # If amount has formatting, create clean copy value
        if raw_amount != 'N/A' and raw_amount != 'PARSING FAILED':
            # Remove thousand separators (commas, spaces) for copy value
            copy_amount = raw_amount.replace(',', '').replace(' ', '')

        create_clickable_field(payment_frame, "Amount", display_amount, is_banking=True, copy_value=copy_amount)
        create_clickable_field(payment_frame, "Currency", data.get('currency', 'N/A'))
        create_clickable_field(payment_frame, "Transfer Type", self.invoices[filename]['transfer_type'])

        # Banking section - ALL CLICKABLE
        banking_frame = ttk.LabelFrame(scrollable_frame, text="BANKING DETAILS (Click to Copy)",
                                      padding="10")
        banking_frame.pack(fill=tk.X, pady=5)

        # European banking
        create_clickable_field(banking_frame, "Bank Name", data.get('bank_name', 'N/A'), is_banking=True)
        create_clickable_field(banking_frame, "IBAN", data.get('iban', 'N/A'), is_banking=True)
        create_clickable_field(banking_frame, "BIC/SWIFT", data.get('bic', 'N/A'), is_banking=True)

        # US banking (v2.1.0+)
        if data.get('routing_number', 'PARSING FAILED') != 'PARSING FAILED':
            create_clickable_field(banking_frame, "Routing Number",
                                 data.get('routing_number', 'N/A'), is_banking=True)
        if data.get('account_number', 'PARSING FAILED') != 'PARSING FAILED':
            create_clickable_field(banking_frame, "Account Number",
                                 data.get('account_number', 'N/A'), is_banking=True)

        # UK banking (v2.1.0+)
        if data.get('sort_code', 'PARSING FAILED') != 'PARSING FAILED':
            create_clickable_field(banking_frame, "Sort Code",
                                 data.get('sort_code', 'N/A'), is_banking=True)

        # Payment method
        if data.get('payment_method', 'PARSING FAILED') != 'PARSING FAILED':
            create_clickable_field(banking_frame, "Payment Method",
                                 data.get('payment_method', 'N/A'), is_banking=True)

        create_clickable_field(banking_frame, "Payment Address",
                             data.get('payment_address', 'N/A'), is_banking=True)

        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Close button and window close handler
        close_btn = ttk.Button(main_frame, text="Close", command=on_close)
        close_btn.pack(pady=(10, 0))

        # Handle window close event (X button)
        detail_window.protocol("WM_DELETE_WINDOW", on_close)

    def open_pdf_file(self, filename):
        """
        Open PDF file with the default system viewer.

        Args:
            filename: The invoice filename to open
        """
        try:
            filepath = self.file_manager.get_full_path(filename)

            if not filepath.exists():
                messagebox.showerror("File Not Found",
                                   f"The file '{filename}' could not be found.")
                return

            # Open with default application based on OS
            system = platform.system()

            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(filepath)], check=True)
            elif system == 'Windows':
                subprocess.run(['start', '', str(filepath)], shell=True, check=True)
            else:  # Linux and others
                subprocess.run(['xdg-open', str(filepath)], check=True)

            self.status_label.config(text=f"Opened: {filename}")

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error Opening File",
                               f"Could not open '{filename}': {e}")
        except Exception as e:
            messagebox.showerror("Error",
                               f"Unexpected error opening '{filename}': {e}")

    def on_tree_motion(self, event):
        """Handle mouse motion to change cursor over filename column."""
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            self.tree.config(cursor='')
            return

        column = self.tree.identify_column(event.x)

        # Change cursor to hand pointer over filename column
        if column == '#1':
            self.tree.config(cursor='hand2')
        else:
            self.tree.config(cursor='')

    def on_tree_click(self, event):
        """Handle clicks on the tree (for checkbox toggles and filename opening)."""
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return

        column = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)

        if not row or row not in self.invoices:
            return

        # Column #1 is Filename - click to open PDF
        if column == '#1':
            self.open_pdf_file(row)
        # Column #8 is Transfer Type, #9 is Payment Set (shifted by 1 for vehicle_id column)
        elif column == '#8':
            # Toggle transfer type checkbox
            var = self.invoices[row]['transfer_var']
            var.set(not var.get())
        elif column == '#9':
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
            current_values[3],  # vehicle_id
            current_values[4],  # amount
            current_values[5],  # currency
            current_values[6],  # banking
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
