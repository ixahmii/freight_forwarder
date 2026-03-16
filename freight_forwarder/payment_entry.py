import frappe
from frappe import _
from frappe.utils import nowdate

@frappe.whitelist()
def create_receive_payment(freight_job):
    """
    Creates a Payment Entry (Receive) for a Freight Job.
    Enhanced with comprehensive validation and error handling.
    """
    try:
        # Step 1: Validate freight job exists
        if not frappe.db.exists("Freight Job", freight_job):
            frappe.throw(
                _("Freight Job '{0}' not found").format(freight_job)
            )

        # Step 2: Find unpaid Sales Invoice
        si_list = frappe.get_all(
            "Sales Invoice",
            filters={
                "freight_job": freight_job,
                "docstatus": 1,
                "outstanding_amount": [">", 0]
            },
            fields=["name", "customer", "outstanding_amount", "debit_to", "company"],
            limit=1
        )

        if not si_list:
            frappe.throw(
                _("No unpaid Sales Invoice found for Freight Job {0}. \n\nPossible reasons:\n1. No Sales Invoice created\n2. Sales Invoice already paid\n3. Sales Invoice is in Draft status").format(
                    frappe.bold(freight_job)
                )
            )

        si = frappe.get_doc("Sales Invoice", si_list[0].name)

        # Step 3: Validate company
        if not si.company:
            frappe.throw(
                _("Sales Invoice {0} has no company assigned").format(
                    frappe.bold(si.name)
                )
            )

        # Step 4: Get default bank account
        bank_account = frappe.get_value(
            "Company",
            si.company,
            "default_bank_account"
        )

        if not bank_account:
            frappe.throw(
                _("Default Bank Account is not configured for company {0}. Please set it in Company settings.").format(
                    frappe.bold(si.company)
                )
            )

        # Step 5: Validate outstanding amount
        if si.outstanding_amount <= 0:
            frappe.throw(
                _("Sales Invoice {0} has no outstanding amount to collect").format(
                    frappe.bold(si.name)
                )
            )

        # Step 6: Create Payment Entry
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": si.customer,
            "company": si.company,
            "posting_date": nowdate(),
            "paid_from": si.debit_to,  # Customer Receivable
            "paid_to": bank_account,   # Bank account
            "paid_amount": si.outstanding_amount,
            "received_amount": si.outstanding_amount,
            "reference_no": f"INV-{si.name}",
            "reference_date": nowdate(),
            "remarks": f"Payment for Freight Job {freight_job}",
            "references": [{
                "reference_doctype": "Sales Invoice",
                "reference_name": si.name,
                "allocated_amount": si.outstanding_amount
            }]
        })

        # Step 7: Insert and submit
        pe.insert(ignore_permissions=True)
        pe.submit()

        # Step 8: Add comment to job
        job = frappe.get_doc("Freight Job", freight_job)
        job.add_comment(
            "Comment",
            _("Payment Entry {0} created for amount {1}").format(
                frappe.bold(pe.name),
                f"{si.outstanding_amount} {si.currency or 'USD'}"
            )
        )

        frappe.msgprint(
            _("Payment Entry {0} created successfully").format(
                frappe.bold(pe.name)
            ),
            alert=True,
            indicator="green"
        )

        return pe.name

    except frappe.DoesNotExistError:
        frappe.throw(
            _("Freight Job '{0}' not found").format(freight_job)
        )
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("create_receive_payment"))
        frappe.throw(
            _("Error creating Payment Entry: {0}").format(str(e))
        )

    return pe.name

    return pe.name
