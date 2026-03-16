import frappe
from frappe import _
from decimal import Decimal

def validate(doc, method):
    """
    Validates Job Cost Sheet before saving.
    Checks for duplicates, calculates totals, and validates amounts.
    """

    # Validation 1: Check for duplicate active cost sheets
    existing = frappe.db.exists(
        "Job Cost Sheet",
        {
            "job": doc.job,
            "docstatus": ["!=", 2],  # Not cancelled
            "name": ["!=", doc.name]
        }
    )

    if existing:
        frappe.throw(
            _("An active Job Cost Sheet already exists for this job: {0}").format(
                frappe.bold(existing)
            )
        )

    # Validation 2: Check if job exists
    if not frappe.db.exists("Freight Job", doc.job):
        frappe.throw(
            _("Freight Job '{0}' does not exist").format(doc.job)
        )

    # Validation 3: Require at least one cost item
    if not doc.cost_items or len(doc.cost_items) == 0:
        frappe.throw(
            _("At least one cost item must be added to the Job Cost Sheet")
        )

    # Validation 4: Validate individual cost items
    calculated_total = Decimal("0")

    for idx, item in enumerate(doc.cost_items, 1):
        # Check required fields
        if not item.expense_type:
            frappe.throw(
                _("Row {0}: Expense Type is required").format(idx)
            )

        # Check amount
        if item.amount is None or item.amount < 0:
            frappe.throw(
                _("Row {0}: Amount must be greater than or equal to 0").format(idx)
            )

        # Check currency
        if not item.currency:
            item.currency = doc.currency or "USD"

        calculated_total += Decimal(str(item.amount))

    # Validation 5: Verify calculated total matches entered total
    if abs(calculated_total - Decimal(str(doc.total_cost or 0))) > Decimal("0.01"):
        frappe.msgprint(
            _("Total Cost has been recalculated to {0} based on cost items").format(
                str(calculated_total) + " " + (doc.currency or "USD")
            ),
            alert=True
        )
        doc.total_cost = float(calculated_total)

    # Validation 6: Check job status (warning only)
    job = frappe.get_doc("Freight Job", doc.job)
    if job.status in ["Draft", "Cancelled"]:
        frappe.msgprint(
            _("Warning: Freight Job {0} is in {1} status. Cost sheet should be created for Active jobs.").format(
                frappe.bold(job.name),
                job.status
            ),
            alert=True,
            indicator="yellow"
        )


def on_submit(doc, method):
    """Actions to perform when Cost Sheet is submitted"""

    job = frappe.get_doc("Freight Job", doc.job)
    job.add_comment(
        "Comment",
        _("Job Cost Sheet {0} submitted with total cost: {1}").format(
            frappe.bold(doc.name),
            str(doc.total_cost) + " " + (doc.currency or "USD")
        )
    )

    frappe.msgprint(
        _("Job Cost Sheet {0} submitted successfully").format(
            frappe.bold(doc.name)
        ),
        alert=True,
        indicator="green"
    )


def on_cancel(doc, method):
    """Actions to perform when Cost Sheet is cancelled"""

    job = frappe.get_doc("Freight Job", doc.job)
    job.add_comment(
        "Comment",
        _("Job Cost Sheet {0} was cancelled").format(frappe.bold(doc.name))
    )
