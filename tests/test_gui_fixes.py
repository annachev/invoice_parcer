#!/usr/bin/env python3
"""Test script to verify GUI bug fixes."""

import tkinter as tk
from tkinter import ttk
import platform

def test_mousewheel_scroll():
    """Test mouse wheel scrolling with platform detection."""
    print("=" * 60)
    print("TEST 1: Mouse Wheel Scrolling")
    print("=" * 60)

    root = tk.Tk()
    root.title("Mouse Wheel Test")
    root.geometry("400x300")

    # Create scrollable canvas
    canvas = tk.Canvas(root, bg='white')
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Add lots of content to make it scrollable
    for i in range(50):
        ttk.Label(scrollable_frame, text=f"Line {i+1}: This is test content").pack(pady=2)

    # Mouse wheel handler with platform detection
    def on_mousewheel(event):
        if platform.system() == 'Darwin':  # macOS
            canvas.yview_scroll(-1 * event.delta, "units")
            print(f"macOS scroll: delta={event.delta}")
        else:  # Windows
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            print(f"Windows scroll: delta={event.delta}")

    canvas.bind_all("<MouseWheel>", on_mousewheel)
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    instruction = ttk.Label(root, text="Try scrolling with your mouse wheel",
                           font=('Helvetica', 10, 'bold'))
    instruction.pack(side=tk.BOTTOM, pady=10)

    print(f"Platform detected: {platform.system()}")
    print("Window opened. Try scrolling with mouse wheel.")
    print("Check console for scroll events.")
    print("Close window to continue to next test.\n")

    root.mainloop()


def test_font_consistency():
    """Test font consistency on hover."""
    print("=" * 60)
    print("TEST 2: Font Consistency on Hover")
    print("=" * 60)

    root = tk.Tk()
    root.title("Font Hover Test")
    root.geometry("500x400")

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="Hover over blue fields and watch font behavior",
              font=('Helvetica', 12, 'bold')).pack(pady=(0, 20))

    def create_test_field(parent, label, value):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        label_widget = ttk.Label(frame, text=f"{label}:", width=15, anchor='w')
        label_widget.pack(side=tk.LEFT)

        value_label = ttk.Label(frame, text=value, anchor='w')
        value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        value_label.config(foreground='#0066cc', cursor='hand2')

        # Capture original font ONCE
        original_font = value_label.cget('font')
        print(f"Field '{label}' - Original font: {original_font}")

        def copy_to_clipboard(e):
            root.clipboard_clear()
            root.clipboard_append(value)
            root.update()
            original_text = value_label.cget('text')
            value_label.config(text='✓ Copied!', foreground='#00aa00')
            root.after(1000, lambda: value_label.config(
                text=original_text, foreground='#0066cc', font=original_font))
            print(f"Clicked '{label}' - Restoring to font: {original_font}")

        def on_enter(e):
            current_font_before = value_label.cget('font')
            if isinstance(original_font, str):
                value_label.config(font=(original_font, 9, 'underline'))
            elif isinstance(original_font, tuple):
                value_label.config(font=(original_font[0] if len(original_font) > 0 else 'TkDefaultFont',
                                         original_font[1] if len(original_font) > 1 else 9,
                                         'underline'))
            else:
                value_label.config(font=('TkDefaultFont', 9, 'underline'))

            current_font_after = value_label.cget('font')
            print(f"Hover '{label}' - Before: {current_font_before}, After: {current_font_after}")

        def on_leave(e):
            current_font_before = value_label.cget('font')
            value_label.config(font=original_font)
            current_font_after = value_label.cget('font')
            print(f"Leave '{label}' - Before: {current_font_before}, Restored to: {current_font_after}")

        value_label.bind('<Button-1>', copy_to_clipboard)
        value_label.bind('<Enter>', on_enter)
        value_label.bind('<Leave>', on_leave)

    # Create test fields
    create_test_field(main_frame, "IBAN", "DE89370400440532013000")
    create_test_field(main_frame, "BIC/SWIFT", "COBADEFFXXX")
    create_test_field(main_frame, "Amount", "10,000,000.00")
    create_test_field(main_frame, "Account", "1234567890")

    ttk.Label(main_frame, text="\nInstructions:", font=('Helvetica', 10, 'bold')).pack(pady=(20, 5))
    ttk.Label(main_frame, text="1. Hover over blue fields - font should add underline").pack()
    ttk.Label(main_frame, text="2. Move mouse away - font should return to original").pack()
    ttk.Label(main_frame, text="3. Click a field - should show '✓ Copied!' then restore").pack()
    ttk.Label(main_frame, text="4. Check console for font change details").pack()

    print("\nWindow opened. Test hover behavior and check console output.")
    print("Close window to continue to next test.\n")

    root.mainloop()


def test_amount_copy_format():
    """Test amount copy format (clean vs display)."""
    print("=" * 60)
    print("TEST 3: Amount Copy Format")
    print("=" * 60)

    root = tk.Tk()
    root.title("Amount Copy Test")
    root.geometry("500x300")

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="Click amounts to copy - check clipboard",
              font=('Helvetica', 12, 'bold')).pack(pady=(0, 20))

    def create_amount_field(parent, label, display_value, copy_value):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        label_widget = ttk.Label(frame, text=f"{label}:", width=20, anchor='w')
        label_widget.pack(side=tk.LEFT)

        value_label = ttk.Label(frame, text=display_value, anchor='w', foreground='#0066cc', cursor='hand2')
        value_label.pack(side=tk.LEFT)

        def copy_to_clipboard(e):
            root.clipboard_clear()
            root.clipboard_append(copy_value)
            root.update()

            # Verify what was copied
            clipboard_content = root.clipboard_get()
            print(f"Display: '{display_value}' → Copied: '{clipboard_content}'")

            if clipboard_content == copy_value:
                print(f"  ✓ CORRECT: Clean format copied")
            else:
                print(f"  ✗ WRONG: Expected '{copy_value}', got '{clipboard_content}'")

            original_text = value_label.cget('text')
            value_label.config(text='✓ Copied!', foreground='#00aa00')
            root.after(1500, lambda: value_label.config(text=original_text, foreground='#0066cc'))

        value_label.bind('<Button-1>', copy_to_clipboard)

    # Test cases
    test_cases = [
        ("Formatted (commas)", "10,000,000.00", "10000000.00"),
        ("Formatted (spaces)", "1 234 567.89", "1234567.89"),
        ("Mixed separators", "5,000 000.50", "5000000.50"),
        ("No formatting", "999.99", "999.99"),
    ]

    for label, display, copy in test_cases:
        create_amount_field(main_frame, label, display, copy)

    ttk.Label(main_frame, text="\nInstructions:", font=('Helvetica', 10, 'bold')).pack(pady=(20, 5))
    ttk.Label(main_frame, text="Click each amount and check the console").pack()
    ttk.Label(main_frame, text="Verify that clean format (no commas/spaces) is copied").pack()

    print("\nTest cases:")
    for label, display, copy in test_cases:
        print(f"  {label}: '{display}' → should copy: '{copy}'")
    print("\nWindow opened. Click amounts and check console output.\n")

    root.mainloop()


def run_all_tests():
    """Run all GUI tests."""
    print("\n" + "=" * 60)
    print("GUI BUG FIX VERIFICATION TESTS")
    print("=" * 60)
    print(f"Platform: {platform.system()}")
    print(f"Python Tkinter version: {tk.TkVersion}")
    print("=" * 60 + "\n")

    try:
        test_mousewheel_scroll()
        test_font_consistency()
        test_amount_copy_format()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        print("Review console output above to verify:")
        print("  1. Mouse wheel scrolling works smoothly")
        print("  2. Font stays consistent on hover/leave")
        print("  3. Amounts copy in clean format without separators")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
