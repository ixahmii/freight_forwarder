import frappe
from frappe.utils import today

@frappe.whitelist()
def create_booking_from_quotation(quotation_name):

    quotation = frappe.get_doc("Freight Quotation", quotation_name)

    # Prevent duplicate booking
    if getattr(quotation, "booking_created", 0):
        frappe.throw("Booking already created for this Quotation")

    # -------------------------------
    # ROUTE VALIDATION
    # -------------------------------

    if not quotation.route:
        frappe.throw("Route details are required before creating Booking.")

    for idx, row in enumerate(quotation.route, start=1):

        if not row.origin or not row.destination:
            frappe.throw(f"Route row {idx}: Origin and Destination are mandatory.")

        if not row.route_code:
            frappe.throw(f"Route row {idx}: Route Code is Required.")

        if not row.service_type:
            frappe.throw(f"Route row {idx}: Service Type is Required.")

    # -------------------------------
    # CHARGES VALIDATION
    # -------------------------------

    if not quotation.charges:
        frappe.throw("At least one charge must be added before creating Booking.")

    for idx, row in enumerate(quotation.charges, start=1):

#        if not row.charge_code:
 #           frappe.throw(f"Charges row {idx}: Charge Code is required.")

        if not row.amount or row.amount <= 0:
            frappe.throw(f"Charges row {idx}: Amount must be greater than zero.")

    # -------------------------------
    # DATE LOGIC
    # -------------------------------

    shipment_date = (
        quotation.get("expected_shipment_date")
        or quotation.get("quotation_date")
        or quotation.get("valid_until")
        or today()
    )

    # -------------------------------
    # CREATE BOOKING
    # -------------------------------

    booking = frappe.get_doc({
        "doctype": "Booking",
        "quotation": quotation.name,
        "customer": quotation.customer,
        "booking_date": shipment_date,
        "service_type": quotation.service_type,
        "origin": quotation.origin,
        "destination": quotation.destination,
        "cargo_description": quotation.cargo_description,
        "weight": quotation.weight,
        "volume": quotation.volume,
        "incoterms": quotation.incoterms,
        "status": "Draft"
    })

    booking.insert(ignore_permissions=True)

    frappe.db.set_value("Freight Quotation", quotation.name, "booking_created", 1)

    return booking.name
