import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controllers.auth_controller import AuthController
from controllers.tracker_controller import TrackerController
from database import init_db


class InventoryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_lab_tracker.db")
        init_db(self.db_path)
        self.auth = AuthController(self.db_path)
        self.tracker = TrackerController(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_roles_and_admin_email_rule(self):
        success, message = self.auth.register_user("Boss", "boss@gmail.com", "Password1!", "admin")
        self.assertFalse(success)
        self.assertNotIn("adminBoss@gmail.com", message)
        self.assertEqual(message, "Invalid admin registration details.")
        self.assertTrue(self.auth.register_user("Boss", "adminBoss@gmail.com", "Password1!", "admin")[0])
        self.assertTrue(self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")[0])
        self.assertFalse(self.auth.login_user("Boss", "adminBoss@gmail.com", "Password1!", "user")[0])
        self.assertTrue(self.auth.login_user("Boss", "adminBoss@gmail.com", "Password1!", "admin")[0])

    def test_admin_can_change_account_password(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.assertTrue(self.auth.admin_change_password("Student", "NewPassword2!")[0])
        self.assertTrue(self.auth.login_user("Student", "student@gmail.com", "NewPassword2!", "user")[0])

    def test_duplicate_names_and_borrowing(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.assertTrue(self.tracker.add_inventory("Laptop", "IT", 1, 50000)[0])
        self.assertFalse(self.tracker.add_inventory("laptop", "Other", 3, 20)[0])
        item_id = self.tracker.fetch_all_inventory()[0][0]
        user_id = self.auth.get_user_id("Student")
        result = self.tracker.borrow_item(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Programming", "Missing")
        self.assertTrue(result[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 0)
        self.assertEqual(self.tracker.fetch_borrow_records()[0][7], "Missing")
        self.assertFalse(self.tracker.borrow_item(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Programming", "Borrowed")[0])

    def test_reservation_requires_approval_and_updates_stock(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.tracker.add_inventory("Camera", "Media", 1, 12000)
        item_id = self.tracker.fetch_all_inventory()[0][0]
        user_id = self.auth.get_user_id("Student")
        self.assertTrue(self.tracker.create_reservation(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Media", "2026-09-10", "10:30")[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 1)
        self.assertTrue(self.tracker.update_reservation_status(1, "Approved")[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 0)
        self.assertEqual(self.tracker.fetch_reservations()[0][9], "Approved")
        borrower = self.tracker.fetch_borrow_records()[0]
        self.assertEqual(borrower[6], 1)
        self.assertEqual(borrower[7], "Borrowed")
        self.assertTrue(self.tracker.update_borrow_status(borrower[0], "Missing")[0])
        self.assertTrue(self.tracker.update_borrow_status(borrower[0], "Returned")[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 1)
        self.assertEqual(self.tracker.fetch_borrow_records()[0][7], "Returned")

    def test_admin_can_place_reservation_on_hold_before_approval(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.tracker.add_inventory("Camera", "Media", 1, 12000)
        item_id = self.tracker.fetch_all_inventory()[0][0]
        user_id = self.auth.get_user_id("Student")
        self.assertTrue(self.tracker.create_reservation(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Media", "2026-09-10", "10:30")[0])
        self.assertTrue(self.tracker.update_reservation_status(1, "On Hold")[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 1)
        self.assertEqual(self.tracker.fetch_reservations()[0][9], "On Hold")
        self.assertTrue(self.tracker.update_reservation_status(1, "Approved")[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 0)

    def test_held_inventory_cannot_be_reserved(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.tracker.add_inventory("Camera", "Media", 1, 12000)
        item_id = self.tracker.fetch_all_inventory()[0][0]
        user_id = self.auth.get_user_id("Student")
        self.assertTrue(self.tracker.set_inventory_hold(item_id)[0])
        result = self.tracker.create_reservation(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Media", "2026-09-10", "10:30")
        self.assertFalse(result[0])
        self.assertIn("on hold", result[1])
        self.assertTrue(self.tracker.set_inventory_hold(item_id, False)[0])
        self.assertTrue(self.tracker.create_reservation(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Media", "2026-09-10", "10:30")[0])

    def test_admin_can_mark_missing_and_return_borrowed_item(self):
        self.auth.register_user("Student", "student@gmail.com", "Password1!", "user")
        self.tracker.add_inventory("Laptop", "IT", 5, 50000)
        item_id = self.tracker.fetch_all_inventory()[0][0]
        user_id = self.auth.get_user_id("Student")
        self.assertTrue(self.tracker.borrow_item(item_id, user_id, "Jane Doe", "ST-001", "BSCS-A", "Programming", "Borrowed", 2)[0])
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 3)
        self.assertTrue(self.tracker.update_borrow_status(1, "Missing")[0])
        self.assertEqual(self.tracker.fetch_borrow_records()[0][7], "Missing")
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 3)
        self.assertTrue(self.tracker.update_borrow_status(1, "Returned")[0])
        self.assertEqual(self.tracker.fetch_borrow_records()[0][7], "Returned")
        self.assertEqual(self.tracker.fetch_all_inventory()[0][3], 5)
        self.assertFalse(self.tracker.update_borrow_status(1, "Returned")[0])


if __name__ == "__main__":
    unittest.main()