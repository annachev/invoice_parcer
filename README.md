# Invoice Parser

**Version:** 2.1.0

An intelligent invoice processing system that extracts key information from PDF invoices using pattern-based parsing with optional ML enhancement.

## Features

- 📄 **Multi-Strategy PDF Parsing**: Automatically selects the best parsing strategy for each invoice
- 🌍 **International Banking Support**: IBAN/BIC (European), ABA routing (US), Sort codes (UK)
- 🔍 **Flexible Pattern Matching**: Recognizes various terminology and formats
- ✅ **Strict Validation**: Checksum validation for IBAN and ABA routing numbers
- 🤖 **Optional ML Enhancement**: spaCy NER and layout classification for improved accuracy
- 🎯 **Smart Confidence Scoring**: Validation-based scoring ensures quality
- 📊 **GUI Application**: Easy-to-use Tkinter interface for invoice processing

---

## Installation

```bash
# Clone repository
git clone <repository-url>
cd invoice_parcer

# Install dependencies
pip install -e .

# (Optional) Install ML dependencies
pip install spacy scikit-learn
python -m spacy download en_core_web_sm

# Run application
python src/invoice_processor/main.py
```

---

## Supported Banking Systems

The invoice parser supports banking information extraction for multiple countries:

### European Banking (SEPA)

- **IBAN**: International Bank Account Number with mod-97 checksum validation
- **BIC/SWIFT**: Bank Identifier Code with format validation
- **Payment Methods**: SEPA, SEPA_INTERNATIONAL
- **Extraction**: Works with or without "IBAN:" label

**Example:**
```
IBAN: DE89 3704 0044 0532 0130 00
BIC: DEUTDEFF
Payment Method: SEPA
```

### United States Banking

- **ABA Routing Number**: 9-digit routing number with checksum validation
- **Account Number**: 6-17 digit account numbers
- **Payment Methods**: ACH (Automated Clearing House)
- **Validation**: Strict ABA checksum algorithm applied

**Supported Labels:**
- `Routing Number:`, `Routing No:`, `Routing #:`
- `ABA Number:`, `ABA:`, `RTN:`
- `ACH Routing:`, `Wire Routing:`

**Example:**
```
Routing Number: 121000248
Account Number: 1234567890
Payment Method: ACH
```

### United Kingdom Banking

- **Sort Code**: 6-digit sort code (format: XX-XX-XX)
- **Account Number**: 8-digit account numbers
- **Payment Methods**: BACS (Bankers' Automated Clearing Services)
- **Validation**: Format validation applied

**Supported Labels:**
- `Sort Code:`, `SC:`
- `Account Number:`, `Account No:`, `Acct #:`, `A/C:`

**Example:**
```
Sort Code: 20-00-00
Account Number: 12345678
Payment Method: BACS
```

### Flexible Account Number Extraction

The parser uses smart context-aware extraction:
- Recognizes "Account Number:", "Account No:", "Acct #:", "A/C:", "Banking Account:"
- Adapts patterns based on detected routing/sort codes
- Generic fallback for unknown formats

---

## Output Schema

### Extracted Fields

The parser extracts the following fields from invoices:

#### Core Fields
- `sender`: Company/individual who issued the invoice
- `recipient`: Company/individual who receives the invoice
- `amount`: Invoice amount (as string with original formatting)
- `currency`: Currency code (EUR, USD, GBP, etc.)

#### Address Fields
- `sender_address`: Full sender address
- `recipient_address`: Full recipient address

#### Contact Fields
- `sender_email`: Sender email address
- `recipient_email`: Recipient email address

#### European Banking Fields
- `iban`: International Bank Account Number (validated)
- `bic`: Bank Identifier Code / SWIFT code (validated)
- `bank_name`: Name of the bank
- `payment_address`: Payment address if specified

#### US Banking Fields (v2.1.0)
- `routing_number`: ABA/ACH routing number (validated)
- `account_number`: Generic account number (US/UK/other)

#### UK Banking Fields (v2.1.0)
- `sort_code`: UK sort code (normalized to XX-XX-XX format)

#### Payment Method (v2.1.0)
- `payment_method`: Auto-detected payment type
  - `SEPA` - IBAN from SEPA country
  - `SEPA_INTERNATIONAL` - IBAN from non-SEPA country
  - `ACH` - US Automated Clearing House
  - `BACS` - UK Bankers' Automated Clearing Services

All fields default to `"PARSING FAILED"` if not found.

### Example Output

```python
{
    "sender": "Acme Consulting GmbH",
    "recipient": "Tech Solutions Ltd",
    "amount": "1,250.00",
    "currency": "EUR",
    "sender_address": "Hauptstraße 123, 10319 Berlin, Germany",
    "recipient_address": "High Street 456, London, UK",
    "sender_email": "billing@acme-consulting.de",
    "recipient_email": "accounts@techsolutions.com",
    "bank_name": "Deutsche Bank AG",
    "iban": "DE89370400440532013000",
    "bic": "DEUTDEFF",
    "routing_number": "PARSING FAILED",
    "account_number": "PARSING FAILED",
    "sort_code": "PARSING FAILED",
    "payment_method": "SEPA",
    "payment_address": "PARSING FAILED"
}
```

---

## Architecture

### Parsing Strategies

The parser uses multiple strategies to handle different invoice layouts:

1. **TwoColumnStrategy**: Invoices with side-by-side "From:/To:" sections
2. **SingleColumnLabelStrategy**: Invoices with top-to-bottom labels
3. **CompanySpecificStrategy**: Handles known company formats (Anthropic, Deutsche Bahn)
4. **PatternFallbackStrategy**: Generic pattern matching for unstructured invoices

### Strategy Selection

The parser automatically:
1. Detects invoice language (English/German)
2. (Optional) Predicts layout type using ML classifier
3. Tries strategies in optimized order
4. Returns result from best-performing strategy

### Validation & Confidence Scoring

Confidence scores (0.0-1.0) weighted by importance:

- **Critical fields (50%)**: sender, recipient, amount
- **Banking fields (30%)**: IBAN/BIC or Routing/Account with validation
- **Supporting fields (20%)**: currency, emails, addresses

**Banking Validation:**
- IBAN: mod-97 checksum validation
- BIC: 8 or 11 character format validation
- ABA Routing: Checksum algorithm + Federal Reserve district check
- UK Sort Code: 6-digit format validation

---

## ML Enhancement (Optional)

Enable machine learning features for improved accuracy on difficult invoices:

### Features

1. **Layout Classification**: Predicts invoice layout type for optimized strategy order
2. **spaCy NER Ensemble**: Uses named entity recognition as fallback when regex fails
3. **Confidence Merging**: Intelligently combines regex and ML results

### Configuration

Edit `config.yaml`:

```yaml
ml:
  enabled: true  # Master ML toggle

  ner:
    model: "en_core_web_sm"
    confidence_threshold: 0.6

  layout:
    enabled: true
    model_path: null  # Optional: Path to trained model
    optimize_strategy_order: true

  ensemble:
    enabled: true
    prefer_regex: true  # Prefer regex when confidence is similar
    ml_min_confidence: 0.5
```

### Performance Impact

- **Without ML**: ~10ms (simple) to ~1500ms (complex PDFs)
- **With ML**: +50-100ms for NER, +1ms for layout classification
- **Accuracy improvement**: +15-20% on unstructured invoices

See `docs/ML_QUICKSTART.md` for details.

---

## Testing

### Run All Tests

```bash
python tests/automated_test.py
```

### Run International Banking Tests

```bash
python tests/test_international_banking.py
```

### Test Coverage

- ✅ Folder structure validation
- ✅ PDF parser (EUR, USD, German invoices)
- ✅ File manager operations
- ✅ Currency-based transfer type detection
- ✅ Edge cases (corrupted PDFs, missing data)
- ✅ Number format parsing (US vs European)
- ✅ Background scanning simulation
- ✅ Application launch
- ✅ International banking (ABA routing, sort codes, unlabeled IBANs)

---

## Supported Languages

- 🇬🇧 **English**: Full support
- 🇩🇪 **German**: Full support
- 🇺🇸 **US English**: Banking patterns and number formats
- 🇬🇧 **UK English**: Banking patterns

Additional languages can be added by extending `PatternLibrary` patterns.

---

## Supported Currencies

- EUR (Euro)
- USD (US Dollar)
- GBP (British Pound)
- CHF (Swiss Franc)
- And more (extensible via configuration)

---

## File Structure

```
invoice_parcer/
├── src/invoice_processor/
│   ├── core/                    # Configuration and logging
│   ├── parsers/                 # PDF parsing logic
│   │   ├── pattern_library.py  # Regex patterns and validation
│   │   ├── parser_utils.py     # Utility functions
│   │   └── parsing_strategies.py # Strategy implementations
│   ├── ml/                      # Machine learning modules (optional)
│   │   ├── ner_extractor.py    # spaCy NER extraction
│   │   ├── layout_classifier.py # Layout classification
│   │   └── layout_features.py  # Feature extraction
│   └── main.py                  # GUI application
├── tests/                       # Automated tests
│   ├── automated_test.py
│   └── test_international_banking.py
├── docs/                        # Documentation
│   ├── INTERNATIONAL_BANKING.md # Banking support guide
│   ├── ML_QUICKSTART.md         # ML setup guide
│   └── BEST_PRACTICES_IMPROVEMENTS.md
└── config.yaml                  # Configuration file
```

---

## Configuration

Edit `config.yaml` to customize:

```yaml
folders:
  pending: "invoice_processor/invoices/pending"
  processed: "invoice_processor/invoices/processed"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "invoice_processor.log"

ml:
  enabled: false  # Set to true to enable ML features

scanning:
  interval: 10  # Seconds between scans
```

---

## Usage

### GUI Application

```bash
python src/invoice_processor/main.py
```

### Programmatic Usage

```python
from invoice_processor.parsers.pdf_parser import parse_invoice

# Parse a single invoice
result = parse_invoice("path/to/invoice.pdf")

print(f"From: {result['sender']}")
print(f"Amount: {result['amount']} {result['currency']}")
print(f"IBAN: {result['iban']}")
print(f"Payment Method: {result['payment_method']}")
```

---

## Performance

- **Simple invoices**: ~10-20ms
- **Complex invoices**: ~100-1500ms (depending on PDF structure)
- **ML overhead**: +50-100ms (when enabled)

Performance tested on Apple Silicon M1/M2.

---

## Changelog

### v2.1.0 (2026-01-18)

**New Features:**
- ✨ US Banking support (ABA routing numbers with checksum validation)
- ✨ UK Banking support (Sort codes with format validation)
- ✨ Unlabeled IBAN extraction (validated by mod-97 checksum)
- ✨ Flexible account number extraction (multiple label variations)
- ✨ Automatic payment method detection (SEPA, ACH, BACS)
- ✨ Smart context-aware account extraction

**Improvements:**
- Enhanced banking field validation (strict checksums)
- Improved confidence scoring for international payments
- Better pattern matching for varied terminology

**Testing:**
- Added comprehensive international banking unit tests
- All regression tests pass (8/8)
- Zero breaking changes (100% backwards compatible)

### v2.0.0 (Previous)

- Strategy pattern implementation
- ML integration (spaCy NER, layout classification)
- IBAN/BIC validation
- Confidence scoring improvements

---

## Documentation

- [International Banking Support](docs/INTERNATIONAL_BANKING.md) - Complete guide to US/UK/EU banking
- [ML Quick Start](docs/ML_QUICKSTART.md) - How to enable and configure ML features
- [Best Practices](docs/BEST_PRACTICES_IMPROVEMENTS.md) - Validation and improvements guide

---

## License

[Add your license here]

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

---

## Support

For issues or questions:
- Create an issue in the repository
- Check documentation in `docs/` folder
- Review test cases in `tests/` folder

---

## Roadmap

**Planned Features:**
- Additional country support (Australia, Canada, India, Japan, etc.)
- SWIFT message format support
- Invoice template learning
- OCR support for scanned invoices
- REST API for invoice processing
- Batch processing improvements

---

## Credits

Built with:
- [pdfplumber](https://github.com/jsvine/pdfplumber) - PDF extraction
- [spaCy](https://spacy.io/) - Named entity recognition (optional)
- [scikit-learn](https://scikit-learn.org/) - Machine learning (optional)
- [tkinter](https://docs.python.org/3/library/tkinter.html) - GUI framework

---

**Invoice Parser v2.1.0** - Intelligent invoice processing with international banking support
