# Copyright (c) 2026, Ahmad Raza and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class Booking(Document):
    def on_submit(self):
        """This runs when the document is submitted."""
        self.validate_before_submit()

    def validate_before_submit(self):
        # Check Booking Container Detail table is not empty
        if not self.get("booking_container_detail"):
            frappe.throw("Cannot submit. <b>Booking Container Detail</b> table must not be empty.")

        # Check Booking Document table is not empty
        if not self.get("booking_document"):
            frappe.throw("Cannot submit. <b>Booking Document</b> table must not be empty.")
