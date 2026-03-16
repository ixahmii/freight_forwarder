import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_quotation_from_lead(lead_name):
    lead = frappe.get_doc("Lead", lead_name)

    # 1️⃣ Prevent duplicate quotation
    existing = frappe.db.exists("Freight Quotation", {"lead": lead.name})
    if existing:
        frappe.throw(f"Freight Quotation already exists: {existing}")

    # 2️⃣ Resolve base customer name
    base_customer_name = lead.company_name or lead.lead_name
    customer_name = base_customer_name

    # 3️⃣ Check if a Customer or Customer Group already exists with same name
    count = 1
    while frappe.db.exists("Customer", customer_name) or frappe.db.exists("Customer Group", customer_name):
        customer_name = f"{base_customer_name} - {count}"
        count += 1

    # 4️⃣ Ensure Customer exists
    customer = frappe.db.exists("Customer", customer_name)
    if not customer:
        customer_doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Company" if lead.company_name else "Individual",
            "territory": "All Territories"
        })
        customer_doc.insert(ignore_permissions=True)
        customer = customer_doc.name

    # 5️⃣ Create Freight Quotation (DRAFT)
    quotation = frappe.get_doc({
        "doctype": "Freight Quotation",
        "lead": lead.name,
        "customer": customer,
        "service_type": getattr(lead, "service_type", ""),
        "shipment_type": getattr(lead, "shipment_type", ""),
        "origin": getattr(lead, "origin", ""),
        "destination": getattr(lead, "destination", ""),
        "cargo_description": getattr(lead, "cargo_description", ""),
        "weight": getattr(lead, "weight", 0),
        "volume": getattr(lead, "volume", 0),
        "incoterms": getattr(lead, "incoterms", ""),
        "currency": getattr(lead, "currency", "USD")
    })

    quotation.insert(ignore_permissions=True)
    # Keep in DRAFT state so user can edit remaining fields

    return quotation.name
