import frappe
from frappe.utils import today


@frappe.whitelist()
def create_freight_job_from_booking(booking_name):

    booking = frappe.get_doc("Booking", booking_name)

    # ----------------------------------
    # DUPLICATE CHECK
    # ----------------------------------

    if getattr(booking, "freight_job_created", 0):
        frappe.throw("Freight Job already created for this Booking")

    # ----------------------------------
    # CONTAINER VALIDATION
    # ----------------------------------

    if not booking.booking_container_detail:
        frappe.throw("At least one Container Detail is required before creating Freight Job.")

    for idx, row in enumerate(booking.booking_container_detail, start=1):

        if not row.container_type:
            frappe.throw(f"Container row {idx}: Container Type is required.")

        if not row.weight or row.volume <= 0:
            frappe.throw(f"Container row {idx}: Quantity must be greater than zero.")

        if not row.container_no:
            frappe.throw(f"Container row {idx}: Container Number is required.")

    # ----------------------------------
    # DOCUMENT VALIDATION
    # ----------------------------------

    if not booking.booking_document:
        frappe.throw("Booking Documents are required before creating Freight Job.")

    missing_docs = []

    for idx, row in enumerate(booking.booking_document, start=1):

        if not row.document_type:
            frappe.throw(f"Document row {idx}: Document Type is required.")

        if not row.attachment:
            missing_docs.append(row.document_type or f"Row {idx}")

        if hasattr(row, "verified") and not row.verified:
            frappe.throw(f"Document row {idx}: Document must be verified.")

    if missing_docs:
        frappe.throw(
            "Missing document attachments: " + ", ".join(missing_docs)
        )

    # ----------------------------------
    # DATE LOGIC
    # ----------------------------------

    booking_date = booking.get("booking_date") or today()

    # ----------------------------------
    # CREATE FREIGHT JOB
    # ----------------------------------

    freight_job = frappe.get_doc({
        "doctype": "Freight Job",
        "booking": booking.name,
        "customer": booking.customer,
        "quotation": booking.quotation,
        "service_type": booking.service_type,
        "origin": booking.origin,
        "destination": booking.destination,
        "cargo_description": booking.cargo_description,
        "weight": booking.weight,
        "volume": booking.volume,
        "etd": booking.etd,
        "eta": booking.eta,
        "status": "Draft"
    })

    freight_job.insert(ignore_permissions=True)

    frappe.db.set_value("Booking", booking.name, "freight_job_created", 1)

    return freight_job.name
