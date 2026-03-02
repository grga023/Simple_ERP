#!/usr/bin/env python3
"""
Refactor all Serbian field names to English across all Python files
"""

import re
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)

def refactor_file(filepath):
    """Replace Serbian field names with English equivalents"""
    logger.debug(f"Processing file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}", exc_info=True)
        return False
    
    original = content
    
    # Database field names mapping
    replacements = {
        # Orders fields
        'naziv': 'name',
        'cena': 'price',
        'placeno': 'paid',
        'kupac': 'customer',
        'datum': 'date',
        'kolicina': 'quantity',
        'boja': 'color',
        'opis': 'description',
        'slika': 'image',
        'lokacija': 'location',
        # Function/variable names (Serbian)
        'kreiranje': 'create_order_page',
        'porudzbenice': 'new_orders_page',
        'realizovano': 'realized_page',
        'za_dostavu': 'for_delivery_page',
    }
    
    # Variable names in functions (more specific replacements)
    special_replacements = {
        "o = request.form": "form_data = request.form",
        "o = request.get_json()": "data = request.get_json()",
        "o['": "form_data['",
        "o.get(": "form_data.get(",
    }
    
    # Apply simple field name replacements (whole word match)
    for serbian, english in replacements.items():
        # Match as word boundary to avoid partial matches
        pattern = r'\b' + re.escape(serbian) + r'\b'
        content = re.sub(pattern, english, content)
    
    # Apply special replacements (order matters)
    for old, new in special_replacements.items():
        content = content.replace(old, new)
    
    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Refactored file: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to write refactored content to {filepath}: {e}", exc_info=True)
            return False
    logger.debug(f"No changes needed for: {filepath}")
    return False

# Files to refactor
files = [
    'blueprints/orders.py',
    'blueprints/lager.py',
]

# Get parent directory (workspace root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"Base directory: {BASE_DIR}")
logger.info("Starting blueprint refactoring...")

refactored_count = 0
for filepath in files:
    full_path = os.path.join(BASE_DIR, filepath)
    if os.path.exists(full_path):
        if refactor_file(full_path):
            print(f"✓ Refactored: {filepath}")
            refactored_count += 1
        else:
            print(f"- No changes: {filepath}")
    else:
        logger.warning(f"File not found: {filepath}")
        print(f"✗ File not found: {filepath}")

logger.info(f"Refactoring complete. {refactored_count}/{len(files)} files changed")
print("\n✅ Refactoring complete!")
