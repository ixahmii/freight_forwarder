import frappe
from frappe import _

@frappe.whitelist()
def create_freight_job(booking_name):
    """
    Creates a Freight Job from a confirmed Booking.
    Enhanced with comprehensive validation and error handling.
    """
    try:
        booking = frappe.get_doc("Booking", booking_name)

        # ✅ Validation 1: Check if booking is confirmed
        if booking.status != "Confirmed":
            frappe.throw(
                _("Booking must be in 'Confirmed' status. Current status: {0}").format(
                    frappe.bold(booking.status)
                )
            )

        # ✅ Validation 2: Check if already created
        if getattr(booking, "freight_job_created", 0):
            frappe.throw(
                _("Freight Job already created for this Booking")
            )

        # ✅ Validation 3: Check required fields
        required_fields = {
            "customer": "Customer",
            "origin": "Origin Port",
            "destination": "Destination Port"
        }

        for field, label in required_fields.items():
            if not booking.get(field):
                frappe.throw(
                    _("{0} is required to create a Freight Job").format(
                        frappe.bold(label)
                    )
                )

        # ✅ Validation 4: Check date logic
        if booking.etd and booking.eta:
            if booking.etd > booking.eta:
                frappe.throw(
                    _("ETD ({0}) cannot be after ETA ({1})").format(
                        booking.etd, booking.eta
                    )
                )

        # ✅ Validation 5: Check weight and volume
        if (booking.weight and booking.weight <= 0) or (booking.volume and booking.volume <= 0):
            frappe.throw(
                _("Weight and Volume must be greater than 0")
            )

        # All validations passed, create the job
        job = frappe.get_doc({
            "doctype": "Freight Job",
            "booking": booking.name,
            "customer": booking.customer,
            "origin": booking.origin,
            "destination": booking.destination,
            "cargo_description": booking.cargo_description,
            "weight": booking.weight,
            "volume": booking.volume,
            "etd": booking.etd,
            "eta": booking.eta,
            "status": "Draft"
        })

        job.insert(ignore_permissions=True)

        booking.freight_job_created = 1
        booking.save(ignore_permissions=True)

        # Success message
        frappe.msgprint(
            _("Freight Job {0} created successfully").format(
                frappe.bold(job.name)
            ),
            alert=True,
            indicator="green"
        )

        return job.name

    except frappe.DoesNotExistError:
        frappe.throw(
            _("Booking '{0}' not found in system").format(booking_name)
        )
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("create_freight_job"))
        frappe.throw(
            _("Unexpected error while creating Freight Job: {0}").format(str(e))
        )
