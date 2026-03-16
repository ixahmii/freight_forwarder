# Copyright (c) 2026, Ahmad Raza and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class FreightQuotation(Document):
    def validate(self):
        """This runs every time the document is saved."""
        self.calculate_total_sell_amount()

    def on_submit(self):
        """This runs when the document is submitted."""
        self.validate_before_submit()

    def validate_before_submit(self):
        # Check Route table is not empty
        if not self.get("route"):
            frappe.throw("Cannot submit. <b>Route</b> table must not be empty.")

        # Check Charges table is not empty
        if not self.get("charges"):
            frappe.throw("Cannot submit. <b>Charges</b> table must not be empty.")

    def calculate_total_sell_amount(self):
        total = 0
        for row in self.get("charges"):
            total += flt(row.amount)
        self.total_sell_amount = total
