import frappe

@frappe.whitelist()
def create_purchase_invoice(job_cost_sheet):
    jcs = frappe.get_doc("Job Cost Sheet", job_cost_sheet)

    if jcs.docstatus != 1:
        frappe.throw("Job Cost Sheet must be Submitted")

    if not jcs.cost_items:
        frappe.throw("No cost items to bill")

    # Map expense type to account
    expense_account_map = {
        "Freight": "Freight Expenses - FF",
        "Customs": "Customs Expenses - FF",
        "Handling": "Handling Expenses - FF",
        "Storage": "Storage Expenses - FF"
    }

    # Group costs by vendor
    vendor_map = {}
    for row in jcs.cost_items:
        if not row.vendor:
            frappe.throw("Vendor is required for all cost items")
        vendor_map.setdefault(row.vendor, []).append(row)

    created_invoices = []

    for vendor, items in vendor_map.items():
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": vendor,
            "freight_job": jcs.job,
            "items": []
        })

        for item in items:
            pi.append("items", {
                "item_name": item.description or item.expense_type,
                "qty": 1,
                "rate": item.amount,
                "amount": item.amount,
                "expense_account": expense_account_map.get(item.expense_type)
            })

        pi.insert(ignore_permissions=True)
        pi.submit()
        created_invoices.append(pi.name)

    frappe.db.set_value("Job Cost Sheet", jcs.name, "purchase_invoice_created", 1)

    # Return list of created invoices for client-side handling
    return {
        "invoices": created_invoices,
        "message": f"Created {len(created_invoices)} Purchase Invoice(s)"
    }
