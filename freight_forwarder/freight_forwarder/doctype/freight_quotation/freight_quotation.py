# Copyright (c) 2026, Ahmad Raza and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt # Use flt to handle float/currency precision safely

class FreightQuotation(Document):
    def validate(self):
        """This runs every time the document is saved."""
        self.calculate_total_sell_amount()

    def calculate_total_sell_amount(self):
        total = 0
        # 'charges' is the fieldname of your Child Table in the JSON
        for row in self.get("charges"):
            # Ensure we are adding a number, even if 'amount' is empty
            total += flt(row.amount)
        
        self.total_sell_amount = total
