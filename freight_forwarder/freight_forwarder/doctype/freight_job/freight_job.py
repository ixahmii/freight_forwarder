import frappe
from frappe.model.document import Document

class FreightJob(Document):
    def before_submit(self):
        """
        Validate Freight Job before submission:
        - Ensure all child tables are filled
        - Enforce FCL container rule
        - Enforce documents and milestones
        - Require at least 1 submitted Sales & Purchase Invoice
        - Calculate profitability
        """

        # -----------------------------
        # 1️⃣ Validate Operational Child Tables
        # -----------------------------
        operational_tables = {
            "job_container_detail": "Container Details",
            "freight_job_document_checklist": "Document Checklist",
            "freight_job_milestone": "Milestones"
        }

        for fieldname, label in operational_tables.items():
            table_data = getattr(self, fieldname, [])

            # Containers mandatory only for FCL
            if fieldname == "job_container_detail" and self.mode == "FCL" and not table_data:
                frappe.throw(f"Cannot submit: {label} must be filled for FCL shipments.")

            # Other operational tables must not be empty
            elif fieldname != "job_container_detail" and not table_data:
                frappe.throw(f"Cannot submit: {label} must be filled before submitting Freight Job.")

            # Check for empty rows
            for idx, row in enumerate(table_data, start=1):
                if not any(value for key, value in row.as_dict().items()
                           if key not in ("name", "parent", "parenttype", "parentfield", "idx")):
                    frappe.throw(f"Cannot submit: {label} row {idx} is empty.")

        # -----------------------------
        # 2️⃣ Validate linked Sales & Purchase Invoices
        # Only enforce at submission (docstatus 1)
        # -----------------------------
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={"freight_job": self.name, "docstatus": 1},
            fields=["name", "grand_total"]
        )
        purchase_invoices = frappe.get_all(
            "Purchase Invoice",
            filters={"freight_job": self.name, "docstatus": 1},
            fields=["name", "grand_total"]
        )

        if self.docstatus == 1:  # Only check at actual submission
            if not sales_invoices:
                frappe.throw("Cannot submit: At least one submitted Sales Invoice must be linked.")
            if not purchase_invoices:
                frappe.throw("Cannot submit: At least one submitted Purchase Invoice must be linked.")

        # -----------------------------
        # 3️⃣ Auto-calculate total revenue and cost
        # Draft or submitted jobs can have invoices prepared
        # -----------------------------
        self.total_revenue = sum(inv.grand_total for inv in sales_invoices)
        self.total_cost = sum(inv.grand_total for inv in purchase_invoices)

        # -----------------------------
        # 4️⃣ Calculate Gross Profit and GP%
        # -----------------------------
        self.gross_profit = self.total_revenue - self.total_cost
        self.gp_ = (self.gross_profit / self.total_revenue * 100) if self.total_revenue else 0

        # -----------------------------
        # 5️⃣ Optional: Professional message
        # -----------------------------
        if self.docstatus == 1:
            frappe.msgprint(
                f"Freight Job validated successfully.\n"
                f"Total Revenue: {self.total_revenue}\n"
                f"Total Cost: {self.total_cost}\n"
                f"Gross Profit: {self.gross_profit}\n"
                f"GP%: {self.gp_:.2f}%"
            )


# -----------------------------
# 6️⃣ Hook: Auto-update Profitability on Invoice Submit/Cancel
# -----------------------------
@frappe.whitelist()
def update_profitability_from_invoice(doc=None, method=None):
    """
    Recalculates total revenue, total cost, gross profit, GP% for Freight Job
    when a linked Sales or Purchase Invoice is submitted or canceled.
    Safe for Draft or Submitted Freight Jobs.
    """
    if not doc:
        return

    freight_job_name = getattr(doc, "freight_job", None)
    if not freight_job_name:
        return

    if not frappe.db.exists("Freight Job", freight_job_name):
        return

    # Aggregate submitted Sales Invoices
    total_revenue = sum(
        inv.grand_total for inv in frappe.get_all(
            "Sales Invoice",
            filters={"freight_job": freight_job_name, "docstatus": 1},
            fields=["grand_total"]
        )
    )

    # Aggregate submitted Purchase Invoices
    total_cost = sum(
        inv.grand_total for inv in frappe.get_all(
            "Purchase Invoice",
            filters={"freight_job": freight_job_name, "docstatus": 1},
            fields=["grand_total"]
        )
    )

    gross_profit = total_revenue - total_cost
    gp_percent = (gross_profit / total_revenue * 100) if total_revenue else 0

    # Update Freight Job fields safely
    frappe.db.set_value("Freight Job", freight_job_name, "total_revenue", total_revenue)
    frappe.db.set_value("Freight Job", freight_job_name, "total_cost", total_cost)
    frappe.db.set_value("Freight Job", freight_job_name, "gross_profit", gross_profit)
    frappe.db.set_value("Freight Job", freight_job_name, "gp_", gp_percent)
