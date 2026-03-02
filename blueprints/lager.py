from flask import Blueprint, request, jsonify, render_template, current_app
import logging
from flask_login import login_required, current_user
import time
import os
from models import db, LagerItem

lager_bp = Blueprint('lager', __name__)
logger = logging.getLogger(__name__)


# ─── Page Route ────────────────────────────────────────────────

@lager_bp.route('/inventory')
@lager_bp.route('/inventory.html')
@login_required
def inventory_page():
    logger.debug(f"Inventory page accessed by user: {current_user.username if hasattr(current_user, 'username') else 'unknown'}")
    return render_template('inventory.html')


# ─── API Routes ────────────────────────────────────────────────

@lager_bp.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    logger.debug("Fetching all inventory items")
    try:
        items = LagerItem.query.all()
        logger.debug(f"Retrieved {len(items)} inventory items")
        return jsonify([i.to_dict() for i in items])
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}", exc_info=True)
        return jsonify({'error': f'Greška pri učitavanju inventara: {str(e)}'}), 500


@lager_bp.route('/api/inventory', methods=['POST'])
@login_required
def add_inventory():
    logger.info("Adding new inventory item")
    try:
        form_data = request.form
        file = request.files.get('image')
        filename = ''
        if file and file.filename:
            filename = f"{int(time.time())}_{file.filename}"
            filepath = os.path.join(current_app.config['IMAGES_DIR'], filename)
            file.save(filepath)
            logger.debug(f"Image saved: {filename}")

        # Validate required fields
        if not form_data.get('name'):
            logger.warning("Add inventory failed: missing name")
            return jsonify({'error': 'Naziv je obavezan'}), 400
        
        try:
            price = float(form_data.get('price', 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid price value: {form_data.get('price')}")
            price = 0.0
        
        try:
            quantity = int(form_data.get('quantity', 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid quantity value: {form_data.get('quantity')}")
            quantity = 0

        item = LagerItem(
            name=form_data.get('name', ''),
            price=price,
            color=form_data.get('color', ''),
            quantity=quantity,
            location=form_data.get('location', 'House'),
            image=filename
        )
        db.session.add(item)
        db.session.commit()
        logger.debug(f"Inventory item added: {item.name} (ID: {item.id}, Qty: {quantity})")
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        logger.exception("Error adding inventory item")
        return jsonify({'error': f'Greška pri dodavanju artikla: {str(e)}'}), 500


@lager_bp.route('/api/inventory/<int:item_id>', methods=['DELETE'])
@login_required
def delete_inventory(item_id):
    logger.info(f"Deleting inventory item: {item_id}")
    item = db.session.get(LagerItem, item_id)
    if not item:
        logger.warning(f"Delete failed: Inventory item {item_id} not found")
        return jsonify({'error': 'Artikal nije pronađen'}), 404
    
    item_name = item.name
    db.session.delete(item)
    db.session.commit()
    logger.debug(f"Inventory item deleted: {item_name} (ID: {item_id})")
    return jsonify({'ok': True})


@lager_bp.route('/api/inventory/<int:item_id>/increase_quantity', methods=['POST'])
@login_required
def increase_quantity(item_id):
    logger.debug(f"Increasing quantity for inventory item: {item_id}")
    item = db.session.get(LagerItem, item_id)
    if not item:
        logger.warning(f"Increase quantity failed: Item {item_id} not found")
        return jsonify({'error': 'Artikal nije pronađen'}), 404
    
    data = request.get_json()
    increase_by = int(data.get('quantity', 0))
    
    if increase_by <= 0:
        logger.warning(f"Invalid quantity increase: {increase_by}")
        return jsonify({'error': 'Količina mora biti veća od 0'}), 400
    
    old_quantity = item.quantity
    item.quantity += increase_by
    db.session.commit()
    logger.debug(f"Inventory quantity increased for {item.name} (ID: {item_id}): {old_quantity} -> {item.quantity}")
    return jsonify({'ok': True, 'new_quantity': item.quantity})
