import csv
from datetime import datetime
from pydantic import ValidationError

from database import DatabaseError, connect
from models.schemas import BorrowSchema, InventorySchema, ReservationSchema
from utils.logger import logger


class TrackerController:
    def __init__(self, db_name=None):
        self.db_name = db_name
        self.logger = logger

    def fetch_all_inventory(self):
        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT id, item_name, category, quantity, unit_price, availability_status FROM inventory ORDER BY id")
            rows = cursor.fetchall()
            conn.close()
            return rows
        except DatabaseError as exc:
            self.logger.error("Failed to fetch inventory records %s", exc)
            return []

    def get_total_asset_value(self):
        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(quantity * unit_price) FROM inventory")
            result = cursor.fetchone()[0]
            conn.close()
            return result if result else 0
        except DatabaseError as exc:
            self.logger.error("Failed to calculate total asset value: %s", exc)
            return 0

    def add_inventory(self, item_name, category, quantity, unit_price):
        try:
            validated = InventorySchema(item_name=item_name, category=category, quantity=quantity, unit_price=unit_price)
        except ValidationError as exc:
            error = exc.errors()[0]
            field_name = error.get("loc", ["field"])[0]
            msg = f"{field_name.capitalize()} {error['msg']}"
            self.logger.warning("Add inventory validation failed: %s", msg)
            return False, f"Validation Error: {msg}"

        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()

            # Check if item with same name and category already exists
            cursor.execute("SELECT id FROM inventory WHERE LOWER(item_name) = LOWER(?)", (validated.item_name,))
            existing_item = cursor.fetchone()

            if existing_item:
                conn.close()
                self.logger.warning("Duplicate item attempted: '%s' in category '%s'", validated.item_name, validated.category)
                return False, f"Item '{validated.item_name}' already exists. Update the existing item instead."

            cursor.execute(
                "INSERT INTO inventory (item_name, category, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (validated.item_name, validated.category, validated.quantity, validated.unit_price),
            )
            conn.commit()
            conn.close()
            self.logger.info("Inventory item added: '%s'", validated.item_name)
            return True, "Inventory item added successfully!"
        except DatabaseError as exc:
            self.logger.error("Error adding inventory: %s", exc)
            return False, "Database insertion failed."

    def update_inventory(self, item_id, item_name, category, quantity, unit_price):
        try:
            validated = InventorySchema(item_name=item_name, category=category, quantity=quantity, unit_price=unit_price)
        except ValidationError as exc:
            error = exc.errors()[0]
            field_name = error.get("loc", ["field"])[0]
            msg = f"{field_name.capitalize()} {error['msg']}"
            return False, f"Validation Error: {msg}"

        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM inventory WHERE LOWER(item_name) = LOWER(?) AND id != ?",
                (validated.item_name, item_id),
            )
            if cursor.fetchone():
                conn.close()
                return False, f"Item '{validated.item_name}' already exists."
            cursor.execute(
                "UPDATE inventory SET item_name = ?, category = ?, quantity = ?, unit_price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (validated.item_name, validated.category, validated.quantity, validated.unit_price, item_id),
            )
            conn.commit()
            conn.close()
            self.logger.info("Inventory ID %s updated", item_id)
            return True, "Inventory item updated successfully!"
        except DatabaseError as exc:
            self.logger.error("Error updating inventory: %s", exc)
            return False, "Database update failed."

    def delete_inventory(self, item_id):
        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            self.logger.info("Inventory ID %s deleted", item_id)
            return True, "Inventory item deleted successfully!"
        except DatabaseError as exc:
            self.logger.error("Error deleting inventory: %s", exc)
            return False, "Database deletion failed."

    def set_inventory_hold(self, item_id, on_hold=True):
        status = "On Hold" if on_hold else "Available"
        try:
            conn = connect(self.db_name)
            cursor = conn.execute(
                "UPDATE inventory SET availability_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, item_id),
            )
            conn.commit()
            conn.close()
            if cursor.rowcount != 1:
                return False, "Inventory item not found."
            return True, f"Inventory item marked {status.lower()}."
        except DatabaseError as exc:
            self.logger.error("Error updating inventory availability: %s", exc)
            return False, "Could not update inventory availability."

    def borrow_item(self, item_id, user_id, student_name, student_id, section, course, status, quantity=1):
        try:
            borrow = BorrowSchema(
                student_name=student_name, student_id=student_id, section=section,
                course=course, status=status, quantity=quantity,
            )
        except ValidationError as exc:
            return False, f"Validation Error: {exc.errors()[0]['msg']}"

        conn = connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            if not item:
                return False, "Inventory item not found."
            if item[0] < borrow.quantity:
                return False, "This item is out of stock."
            cursor.execute(
                "UPDATE inventory SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND quantity >= ?",
                (borrow.quantity, item_id, borrow.quantity),
            )
            if cursor.rowcount != 1:
                return False, "This item is out of stock."
            cursor.execute(
                "INSERT INTO borrow_records (inventory_id, user_id, student_name, student_id, section, course, quantity, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, user_id, borrow.student_name, borrow.student_id, borrow.section, borrow.course, borrow.quantity, borrow.status),
            )
            conn.commit()
            return True, "Borrow record saved."
        except DatabaseError as exc:
            conn.rollback()
            self.logger.error("Error saving borrow record: %s", exc)
            return False, "Could not save borrow record."
        finally:
            conn.close()

    def fetch_borrow_records(self):
        conn = connect(self.db_name)
        try:
            return conn.execute(
                """SELECT br.id, i.item_name, br.student_name, br.student_id,
                          br.section, br.course, br.quantity, br.status, br.borrowed_at
                   FROM borrow_records br JOIN inventory i ON i.id = br.inventory_id
                   ORDER BY br.borrowed_at DESC"""
            ).fetchall()
        finally:
            conn.close()

    def fetch_user_borrow_records(self, user_id):
        conn = connect(self.db_name)
        try:
            return conn.execute(
                """SELECT br.id, i.item_name, br.student_name, br.student_id,
                          br.section, br.course, br.quantity, br.status,
                          br.borrowed_at, br.returned_at
                   FROM borrow_records br JOIN inventory i ON i.id = br.inventory_id
                   WHERE br.user_id = ?
                   ORDER BY br.borrowed_at DESC""",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

    def update_borrow_status(self, record_id, status):
        if status not in {"Missing", "Returned"}:
            return False, "Invalid borrower record status."
        conn = connect(self.db_name)
        try:
            row = conn.execute(
                "SELECT inventory_id, quantity, status FROM borrow_records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if not row:
                return False, "Borrower record not found."
            if row[2] == "Returned":
                return False, "This item has already been returned."
            if status == "Missing":
                conn.execute("UPDATE borrow_records SET status = ? WHERE id = ?", (status, record_id))
            else:
                updated = conn.execute(
                    "UPDATE borrow_records SET status = ?, returned_at = CURRENT_TIMESTAMP WHERE id = ? AND status != 'Returned'",
                    (status, record_id),
                )
                if updated.rowcount != 1:
                    return False, "This item has already been returned."
                conn.execute(
                    "UPDATE inventory SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (row[1], row[0]),
                )
            conn.commit()
            return True, f"Borrower record marked {status.lower()}."
        except DatabaseError as exc:
            conn.rollback()
            self.logger.error("Error updating borrower record: %s", exc)
            return False, "Could not update borrower record."
        finally:
            conn.close()

    def fetch_inventory_status(self):
        conn = connect(self.db_name)
        try:
            return conn.execute(
                """SELECT i.id, i.item_name, i.quantity,
                          COALESCE(SUM(CASE WHEN br.status IN ('Borrowed', 'Missing') THEN 1 ELSE 0 END), 0),
                          COALESCE(SUM(CASE WHEN r.status = 'Pending' THEN 1 ELSE 0 END), 0)
                   FROM inventory i
                   LEFT JOIN borrow_records br ON br.inventory_id = i.id
                   LEFT JOIN reservations r ON r.inventory_id = i.id
                   GROUP BY i.id ORDER BY i.id"""
            ).fetchall()
        finally:
            conn.close()

    def create_reservation(self, item_id, user_id, student_name, student_id, section, course, reservation_date, reservation_time, quantity=1):
        try:
            reservation = ReservationSchema(
                student_name=student_name, student_id=student_id, section=section,
                course=course, reservation_date=reservation_date, reservation_time=reservation_time, quantity=quantity,
            )
        except ValidationError as exc:
            return False, f"Validation Error: {exc.errors()[0]['msg']}"
        conn = connect(self.db_name)
        try:
            item = conn.execute("SELECT quantity, availability_status FROM inventory WHERE id = ?", (item_id,)).fetchone()
            if not item or item[0] < reservation.quantity:
                return False, "This item is out of stock."
            if item[1] == "On Hold":
                return False, "This item is currently on hold and cannot be reserved."
            pending = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM reservations WHERE inventory_id = ? AND status = 'Pending'",
                (item_id,),
            ).fetchone()[0]
            if pending + reservation.quantity > item[0]:
                return False, "That quantity exceeds the units still available for reservation."
            conn.execute(
                "INSERT INTO reservations (inventory_id, user_id, student_name, student_id, section, course, quantity, reservation_date, reservation_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, user_id, reservation.student_name, reservation.student_id, reservation.section, reservation.course, reservation.quantity, reservation.reservation_date, reservation.reservation_time),
            )
            conn.commit()
            return True, "Reservation submitted for admin approval."
        finally:
            conn.close()

    def fetch_reservations(self):
        conn = connect(self.db_name)
        try:
            return conn.execute(
                """SELECT r.id, i.item_name, r.student_name, r.student_id,
                          r.section, r.course, r.quantity, r.reservation_date, r.reservation_time, r.status
                   FROM reservations r JOIN inventory i ON i.id = r.inventory_id
                   ORDER BY r.created_at DESC"""
            ).fetchall()
        finally:
            conn.close()

    def fetch_user_reservations(self, user_id):
        conn = connect(self.db_name)
        try:
            return conn.execute(
                """SELECT r.id, i.item_name, r.student_name, r.student_id,
                          r.section, r.course, r.quantity, r.reservation_date,
                          r.reservation_time, r.status, r.created_at
                   FROM reservations r JOIN inventory i ON i.id = r.inventory_id
                   WHERE r.user_id = ?
                   ORDER BY r.created_at DESC""",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

    def update_reservation_status(self, reservation_id, status):
        if status not in {"Approved", "On Hold", "Rejected"}:
            return False, "Invalid reservation status."
        conn = connect(self.db_name)
        try:
            row = conn.execute(
                """SELECT inventory_id, user_id, student_name, student_id, section, course,
                          quantity, status
                   FROM reservations WHERE id = ?""",
                (reservation_id,),
            ).fetchone()
            if not row:
                return False, "Reservation not found."
            if row[7] not in {"Pending", "On Hold"}:
                return False, "This reservation has already been reviewed."
            if status == "Approved":
                quantity = row[6]
                updated = conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ? AND quantity >= ?", (quantity, row[0], quantity))
                if updated.rowcount != 1:
                    return False, "This item is no longer in stock."
                conn.execute(
                    """INSERT INTO borrow_records
                       (inventory_id, user_id, student_name, student_id, section, course, quantity, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'Borrowed')""",
                    (row[0], row[1], row[2], row[3], row[4], row[5], quantity),
                )
            conn.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, reservation_id))
            conn.commit()
            return True, f"Reservation {status.lower()}."
        finally:
            conn.close()

    def export_to_csv(self, filename=None):
        if filename is None:
            filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT id, item_name, category, quantity, unit_price FROM inventory ORDER BY id")
            rows = cursor.fetchall()
            conn.close()

            total_value = self.get_total_asset_value()

            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['ID', 'Item Name', 'Category', 'Quantity', 'Unit Price', 'Total Value']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in rows:
                    item_id, item_name, category, quantity, unit_price = row
                    item_total = quantity * unit_price
                    writer.writerow({
                        'ID': item_id,
                        'Item Name': item_name,
                        'Category': category,
                        'Quantity': quantity,
                        'Unit Price': f"₱{unit_price:.2f}",
                        'Total Value': f"₱{item_total:.2f}"
                    })

                # Add summary row
                writer.writerow({})  # Empty row
                writer.writerow({'ID': 'TOTAL ASSET VALUE', 'Unit Price': f"₱{total_value:.2f}"})

            self.logger.info("CSV report exported: %s", filename)
            return True, f"CSV report exported successfully to {filename}"
        except Exception as exc:
            self.logger.error("Error exporting CSV: %s", exc)
            return False, "Failed to export CSV report."
        except DatabaseError as exc:
            self.logger.error("Error updating status: %s", exc)
            return False, "Failed to update status."

    def delete_experiment(self, exp_id):
        try:
            conn = connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM experiments WHERE id = ?", (exp_id,))
            conn.commit()
            conn.close()
            self.logger.info("Experiment ID %s deleted.", exp_id)
            return True, "Record deleted successfully!"
        except DatabaseError as exc:
            self.logger.error("Error deleting record: %s", exc)
            return False, "Failed to delete record."
