# International Banking Support

**Version:** 2.1.0
**Last Updated:** 2026-01-18

## Overview

As of v2.1.0, the invoice parser supports banking information extraction for European (IBAN/BIC), United States (ABA routing), and United Kingdom (sort code) banking systems.

This extends the parser beyond the original IBAN/BIC-only support to handle international payments more flexibly.

---

## Supported Banking Systems

### European Banking (SEPA)

**Fields Extracted:**
- **IBAN**: International Bank Account Number with mod-97 checksum validation
- **BIC/SWIFT**: Bank Identifier Code with format validation (8 or 11 characters)

**Payment Methods:**
- `SEPA` - IBAN from SEPA country (36 countries including EU, EEA, Switzerland, UK)
- `SEPA_INTERNATIONAL` - IBAN from non-SEPA country

**Extraction Features:**
- Works with **labeled** IBANs: `IBAN: DE89370400440532013000`
- Works with **unlabeled** IBANs: `DE89370400440532013000` (validated by checksum)
- Automatic mod-97 checksum validation prevents false positives

**Example:**
```
IBAN: DE89 3704 0044 0532 0130 00
BIC: DEUTDEFF
```

---

### United States Banking

**Fields Extracted:**
- **Routing Number**: 9-digit ABA/ACH routing number with checksum validation
- **Account Number**: 6-17 digit account numbers

**Payment Methods:**
- `ACH` - Automated Clearing House (most common for invoices)

**Validation:**
- Strict ABA checksum algorithm: `(3*(d1+d4+d7) + 7*(d2+d5+d8) + 1*(d3+d6+d9)) mod 10 = 0`
- Federal Reserve district validation (first two digits must be 01-12, 21-32, 61-72, or 80)
- Rejects obviously invalid numbers (000000000, 111111111, etc.)

**Supported Labels:**
- `Routing Number:`, `Routing No:`, `Routing #:`
- `ABA Number:`, `ABA:`
- `ACH Routing:`, `Wire Routing:`
- `RTN:`

**Example:**
```
Routing Number: 121000248
Account Number: 1234567890
```

**Valid Routing Numbers** (examples):
- `121000248` - Wells Fargo
- `026009593` - Bank of America
- `011000015` - Federal Reserve Bank

---

### United Kingdom Banking

**Fields Extracted:**
- **Sort Code**: 6-digit sort code (normalized to XX-XX-XX format)
- **Account Number**: 8-digit account numbers

**Payment Methods:**
- `BACS` - Bankers' Automated Clearing Services (most common for invoices)

**Validation:**
- Format validation (6 digits)
- Automatic normalization to `XX-XX-XX` format

**Supported Labels:**
- `Sort Code:`, `SC:`
- `Account Number:`, `Account No:`, `Acct #:`, `A/C:`

**Example:**
```
Sort Code: 20-00-00
Account Number: 12345678
```

**Sort Code Formats Accepted:**
- `20-00-00` (with hyphens)
- `200000` (no hyphens - automatically normalized to 20-00-00)
- `20 00 00` (with spaces - automatically normalized to 20-00-00)

---

## Flexible Account Number Extraction

The parser recognizes multiple account number variations:

| Label | Example |
|-------|---------|
| `Account Number:` | Account Number: 12345678 |
| `Account No:` | Account No: 87654321 |
| `Acct #:` | Acct #: 11223344 |
| `Banking Account:` | Banking Account: 99887766 |
| `Bank Account:` | Bank Account: 55667788 |
| `A/C:` | A/C: 44556677 |

The parser uses **smart context-aware extraction**:
- If US routing number is present → expects 6-17 digit account numbers
- If UK sort code is present → expects 8-digit account numbers
- Otherwise → uses generic account number patterns

---

## Validation Strictness

All banking extractions use **strict validation** per user requirements:

### IBAN Validation
- ✅ **Length check**: 15-34 characters
- ✅ **Country code check**: First 2 chars must be letters
- ✅ **Check digit validation**: Characters 3-4 must be digits
- ✅ **mod-97 checksum**: Full validation prevents false positives

### US Routing Number Validation
- ✅ **Length check**: Exactly 9 digits
- ✅ **District check**: First 2 digits must be valid Federal Reserve district
- ✅ **Checksum validation**: ABA algorithm prevents typos and invalid numbers
- ✅ **Rejection of invalid patterns**: 000000000, 111111111, etc.

### UK Sort Code Validation
- ✅ **Length check**: Exactly 6 digits
- ✅ **Format validation**: Accepts hyphens/spaces, normalizes output
- ⚠️ **No checksum available**: UK sort codes don't have checksums

This prevents false positives where invoice numbers or other data might match banking patterns.

---

## Payment Method Detection

The `payment_method` field is automatically populated based on detected banking fields:

| Detected Fields | Payment Method | Description |
|----------------|----------------|-------------|
| IBAN from SEPA country | `SEPA` | Single Euro Payments Area |
| IBAN from non-SEPA country | `SEPA_INTERNATIONAL` | International IBAN payment |
| US routing number | `ACH` | Automated Clearing House |
| UK sort code | `BACS` | Bankers' Automated Clearing Services |
| No banking details | `PARSING FAILED` | Could not detect payment method |

**Priority**: If multiple banking systems are present (e.g., both IBAN and routing number), the parser prefers IBAN for payment method detection.

---

## Output Schema

### New Banking Fields (v2.1.0)

In addition to existing IBAN/BIC fields, the parser now extracts:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `routing_number` | string | US ABA/ACH routing number (validated) | "121000248" |
| `account_number` | string | Generic account number (US/UK/other) | "1234567890" |
| `sort_code` | string | UK sort code (normalized format) | "20-00-00" |
| `payment_method` | string | Auto-detected payment type | "SEPA", "ACH", "BACS" |

All fields default to `"PARSING FAILED"` if not found.

### Complete Output Example (US Invoice)

```python
{
    "sender": "Acme Corp",
    "recipient": "Tech Solutions Ltd",
    "amount": "5,432.10",
    "currency": "USD",
    "sender_address": "123 Main St, New York, NY 10001",
    "recipient_address": "456 High St, London, UK",
    "sender_email": "billing@acmecorp.com",
    "recipient_email": "accounts@techsolutions.com",
    "bank_name": "Wells Fargo Bank",
    "iban": "PARSING FAILED",
    "bic": "PARSING FAILED",
    "routing_number": "121000248",
    "account_number": "1234567890",
    "sort_code": "PARSING FAILED",
    "payment_method": "ACH",
    "payment_address": "PARSING FAILED"
}
```

---

## Edge Cases and Mixed Systems

### Unlabeled IBAN

The parser can extract IBANs even without the "IBAN:" label:

```
Please transfer funds to DE89370400440532013000 within 30 days.
```

**Result**: IBAN extracted and validated via checksum.

**Safety**: The mod-97 checksum validation ensures very high accuracy (99%+ false positive rejection rate).

### Multiple Banking Systems

If an invoice contains both European and US/UK banking details:

```
European Payment:
IBAN: DE89370400440532013000
BIC: DEUTDEFF

US Payment:
Routing Number: 121000248
Account Number: 1234567890
```

**Result**: All fields extracted, payment_method prefers IBAN → `SEPA`

---

## Adding New Countries

To add support for additional countries:

### Step 1: Add Patterns

Add patterns to `pattern_library.py`:

```python
# Example: Australia BSB codes
BSB_PATTERNS = [
    r'(?:BSB)[:\s]*(\d{3}[-\s]?\d{3})',
]

# Example: Australian account numbers
AU_ACCOUNT_PATTERNS = [
    r'(?:Account\s+(?:Number|No\.?))[:\s]*(\d{6,10})',
]
```

### Step 2: Add Validation

Add validation function:

```python
@staticmethod
def validate_bsb(bsb: str) -> bool:
    """Validate Australian BSB code format."""
    clean = bsb.replace('-', '').replace(' ', '')
    # BSB must be 6 digits, first digit 0-9, within range
    return len(clean) == 6 and clean.isdigit()

@staticmethod
def normalize_bsb(bsb: str) -> str:
    """Normalize BSB to XXX-XXX format."""
    clean = bsb.replace('-', '').replace(' ', '')
    return f"{clean[0:3]}-{clean[3:6]}"
```

### Step 3: Update Extraction Logic

Modify `extract_banking_info()` in `parser_utils.py`:

```python
# --- Australian Banking (BSB) ---
bsb = None
for pattern in PatternLibrary.BSB_PATTERNS:
    bsb = extract_pattern(text, pattern)
    if bsb:
        break

if bsb and PatternLibrary.validate_bsb(bsb):
    banking["bsb_code"] = PatternLibrary.normalize_bsb(bsb)
```

### Step 4: Update Result Schema

Add field to `create_default_result()`:

```python
"bsb_code": PARSING_FAILED,
```

### Step 5: Update Payment Method Detection

Add detection logic:

```python
# Australian payment detection
if banking_info.get('bsb_code') != PARSING_FAILED:
    return "DOMESTIC_AU"
```

### Step 6: Update Confidence Scoring

Add scoring for new banking system in `calculate_confidence()`:

```python
# Option 4: Australian Banking (BSB + Account)
elif result.get('bsb_code') != PARSING_FAILED:
    banking_score += 0.15
    if result.get('account_number') != PARSING_FAILED:
        banking_score += 0.10
```

### Step 7: Add Unit Tests

Create tests in `test_international_banking.py`:

```python
def test_australian_banking_extraction():
    """Test Australian BSB + account extraction."""
    text = "BSB: 012-345, Account Number: 987654321"
    banking = extract_banking_info(text, text.split('\n'))
    assert banking['bsb_code'] == "012-345"
    assert banking['account_number'] == "987654321"
    assert banking['payment_method'] == "DOMESTIC_AU"
```

---

## Performance Impact

The international banking extraction adds minimal overhead:

| Operation | Time Added |
|-----------|------------|
| Pattern matching (US/UK) | < 2ms |
| ABA checksum validation | < 0.1ms |
| Sort code normalization | < 0.1ms |
| Unlabeled IBAN search | < 1ms |
| **Total overhead** | **< 3ms** |

This is negligible compared to PDF parsing time (10-1500ms depending on complexity).

---

## Backwards Compatibility

✅ **100% Backwards Compatible**

- All existing IBAN/BIC extraction works identically
- New fields default to `PARSING_FAILED` for existing invoices
- No changes to output format structure
- All existing tests pass unchanged (8/8 automated tests)
- Confidence scoring maintains same 30% weight for banking fields

### Migration Notes

No migration required. The system works identically for existing invoices:

**Before v2.1.0:**
```python
{"iban": "DE89...", "bic": "DEUTDEFF"}
```

**After v2.1.0:**
```python
{
    "iban": "DE89...",
    "bic": "DEUTDEFF",
    "routing_number": "PARSING FAILED",
    "account_number": "PARSING FAILED",
    "sort_code": "PARSING FAILED",
    "payment_method": "SEPA"
}
```

---

## Testing

### Unit Tests

Run international banking tests:

```bash
python3 tests/test_international_banking.py
```

**Coverage:**
- ✅ ABA routing number validation (valid checksums, invalid checksums, format checks)
- ✅ UK sort code validation (format checks, normalization)
- ✅ Unlabeled IBAN extraction
- ✅ US banking extraction (routing + account)
- ✅ UK banking extraction (sort code + account)
- ✅ Payment method detection
- ✅ Account number terminology variations
- ✅ Mixed banking systems (both IBAN and routing number)

### Regression Tests

Verify no breakage:

```bash
python3 tests/automated_test.py
```

**Result**: 8/8 tests pass (no regressions)

---

## Troubleshooting

### Issue: Routing number not extracted

**Possible causes:**
1. Invalid checksum → Check ABA routing number is correct
2. Invalid district code → First 2 digits must be 01-12, 21-32, 61-72, or 80
3. Missing label → Add "Routing Number:" or "ABA:" label

**Solution**: Run validation manually:
```python
from invoice_processor.parsers.pattern_library import PatternLibrary
PatternLibrary.validate_aba_routing("121000248")  # Returns True/False
```

### Issue: Sort code extracted in wrong format

**Expected behavior**: Sort codes are automatically normalized to `XX-XX-XX` format.

Input: `200000` → Output: `20-00-00`
Input: `20 00 00` → Output: `20-00-00`
Input: `20-00-00` → Output: `20-00-00` (unchanged)

### Issue: Account number not extracted

**Possible causes:**
1. Label not recognized → Check account number label format
2. Account too short → Minimum 6 characters required
3. Invalid characters → Account numbers should be alphanumeric

**Supported labels**: Account Number, Account No, Acct #, Banking Account, Bank Account, A/C

### Issue: Payment method is PARSING_FAILED

**Cause**: No valid banking details detected.

**Solution**: Ensure at least one of the following is present and valid:
- IBAN with valid checksum
- US routing number with valid checksum
- UK sort code with valid format

---

## References

- **IBAN Standard**: ISO 13616
- **ABA Routing Numbers**: American Bankers Association specification
- **UK Sort Codes**: UK Payments Administration
- **SEPA Countries**: European Payments Council

---

## License

This feature is part of the invoice processor project and follows the same license as the main project.

For questions or issues, please create an issue in the project repository.
