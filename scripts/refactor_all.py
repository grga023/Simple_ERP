#!/usr/bin/env python3
"""
Complete refactoring: Serbian → English all across codebase
"""

import os
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] - [%(name)s] - %(message)s'
)

# Mapping of Serbian to English
FIELD_MAP = {
    # Database fields
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
}

FUNC_MAP = {
    'kreiranje': 'create_order_page',
    'porudzbenice': 'new_orders_page',
    'realizovano': 'realized_page',
    'za_dostavu': 'for_delivery_page',
    'za_daostavu': 'for_delivery',
}

def refactor_file(filepath):
    """Refactor file by replacing Serbian identifiers with English"""
    logger.debug(f"Processing file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}", exc_info=True)
        return False
    
    original = content
    
    # Replace field mappings (whole word boundaries)
    for serbian, english in FIELD_MAP.items():
        # Pattern matches: variable_name, .attribute, 'key', "key", [key]
        patterns = [
            (r'\[[\s]*[\'\"]' + serbian + r'[\'\"][\s]*\]', f"['{english}']"),  # ['field']
            (r'\[[\s]*[\'\"]' + serbian + r'[\'\"][\s]*\]', f'["{english}"]'),  # ["field"]
            (r'\.(' + serbian + r')\b', f'.{english}'),  # .field
            (r'\(' + serbian + r'[\s]*[,)]', f'({english} '),  # function(field,
            (r'= ' + serbian + r'\b', f'= {english}'),  # = field
            (r'\b(' + serbian + r') =', f'{english} ='),  # field =
        ]
        
        for pattern, repl in patterns:
            content = re.sub(pattern, repl, content)
    
    # Also do simple word replacement for dictionary keys and variables
    for serbian, english in FIELD_MAP.items():
        content = content.replace(f"'{serbian}'", f"'{english}'")
        content = content.replace(f'"{serbian}"', f'"{english}"')
    
    # Replace function names
    for serbian, english in FUNC_MAP.items():
        content = re.sub(r'\b' + serbian + r'\b', english, content)
    
    # Replace variable names in template names
    content = content.replace("'kreiranje.html'", "'create_order.html'")
    content = content.replace("'porudzbenice.html'", "'new_orders.html'")
    content = content.replace("'realizovano.html'", "'realized.html'")
    content = content.replace("'za_dostavu.html'", "'for_delivery.html'")
    content = content.replace("'za_daostavu.html'", "'for_delivery.html'")
    
    # Replace variable name assignments common in code
    content = content.replace("o = request.form", "form_data = request.form")
    content = content.replace("o = request.get_json()", "data = request.get_json()")
    content = content.replace("o['", "form_data['")
    content = content.replace('o["', 'form_data["')
    content = content.replace("o.get(", "form_data.get(")
    
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

# Get workspace root
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"Workspace root: {workspace_root}")

# Files to refactor
files_to_refactor = [
    'blueprints/orders.py',
    'blueprints/lager.py',
    'blueprints/email_notify.py',
    'blueprints/config.py',
    'blueprints/auth.py',
    'ERP_server.py',
]

logger.info("Starting refactoring process...")
print("🔄 Refactoring Python files...")
refactored_count = 0
for filepath in files_to_refactor:
    full_path = os.path.join(workspace_root, filepath)
    if os.path.exists(full_path):
        if refactor_file(full_path):
            print(f"  ✓ {filepath}")
            refactored_count += 1
        else:
            print(f"  - {filepath}")
    else:
        logger.warning(f"File not found: {filepath}")
        print(f"  ✗ Not found: {filepath}")

logger.info(f"Refactoring complete. {refactored_count}/{len(files_to_refactor)} files changed")
print("\n✅ Refactoring complete!")
