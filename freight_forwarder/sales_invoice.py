import frappe
from frappe import _
from decimal import Decimal

def format_currency_safe(amount, currency="USD"):
    """Fallback currency formatter when frappe.format_currency is not available."""
    try:
        amt = Decimal(str(amount))
    except Exception:
        return f"{amount} {currency}"
    return f"{amt:,.2f} {currency}"


@frappe.whitelist()
def create_sales_invoice(freight_job):
    """
    Draft-friendly Sales Invoice creation for Freight Job.
    - Allows Draft or Submitted Freight Jobs
    - Validates Job Cost Sheet, cost items, customer
    - Links invoice to Freight Job
    """
    try:
        # Step 1: Fetch Freight Job
        job = frappe.get_doc("Freight Job", freight_job)

        # Step 2: Check if already invoiced
        if getattr(job, "sales_invoice_created", 0):
            existing_invoice = frappe.db.get_value(
                "Sales Invoice", {"freight_job": job.name, "docstatus": 1}, "name"
            )
            frappe.throw(
                _("Sales Invoice already created for this Freight Job: {0}").format(
                    frappe.bold(existing_invoice)
                )
            )

        # Step 3: Fetch latest Job Cost Sheet (can be draft or submitted)
        jcs_list = frappe.get_all(
            "Job Cost Sheet",
            filters={"job": job.name},
            fields=["name", "total_cost"],
            order_by="modified desc",
            limit=1
        )

        if not jcs_list:
            frappe.throw(
                _("No Job Cost Sheet found for Freight Job {0}. Please create a cost sheet first.").format(
                    frappe.bold(job.name)
                )
            )

        jcs = frappe.get_doc("Job Cost Sheet", jcs_list[0].name)

        # Step 4: Validate cost items
        if not jcs.cost_items or len(jcs.cost_items) == 0:
            frappe.throw(
                _("Job Cost Sheet {0} has no cost items. Please add items before creating invoice.").format(
                    frappe.bold(jcs.name)
                )
            )

        # Step 5: Validate customer
        if not job.customer:
            frappe.throw(_("Freight Job {0} has no customer assigned").format(frappe.bold(job.name)))

        # Step 6: Create Sales Invoice (Draft)
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": job.customer,
            "company": job.company or "Main",
            "freight_job": job.name,
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "items": []
        })

        # Step 7: Add cost items as invoice items
        total_invoice_amount = 0
        for idx, cost_item in enumerate(jcs.cost_items, 1):
            if not cost_item.amount or cost_item.amount < 0:
                frappe.throw(_("Cost Item {0} has invalid amount: {1}").format(idx, cost_item.amount))

            income_account = get_income_account(cost_item.expense_type)
            if not income_account:
                frappe.throw(_("No income account configured for expense type: {0}").format(cost_item.expense_type))

            si.append("items", {
                "item_name": cost_item.description or cost_item.expense_type,
                "qty": 1,
                "rate": cost_item.amount,
                "amount": cost_item.amount,
                "income_account": income_account,
                "cost_center": get_default_cost_center(),
                "description": f"Freight Charge - {cost_item.expense_type}"
            })
            total_invoice_amount += cost_item.amount

        # Step 8: Warning if invoice total differs from cost sheet
        if abs(Decimal(str(total_invoice_amount)) - Decimal(str(jcs.total_cost))) > Decimal("0.01"):
            frappe.msgprint(
                _("Warning: Invoice total ({0}) differs from Cost Sheet total ({1})").format(
                    total_invoice_amount, jcs.total_cost
                ),
                alert=True
            )

        # Step 9: Insert as Draft (do not submit automatically)
        si.insert(ignore_permissions=True)

        # Step 10: Mark job as invoiced (flag can remain but invoice still Draft)
        frappe.db.set_value("Freight Job", job.name, "sales_invoice_created", 1)

        # Step 11: Add comment for audit trail
        job.add_comment(
            "Comment",
            _("Draft Sales Invoice {0} created for total amount {1}").format(
                frappe.bold(si.name),
                format_currency_safe(total_invoice_amount, "USD")
            )
        )

        frappe.msgprint(
            _("Draft Sales Invoice {0} created successfully").format(frappe.bold(si.name)),
            alert=True,
            indicator="blue"
        )

        return si.name

    except frappe.DoesNotExistError:
        frappe.throw(_("Freight Job '{0}' not found").format(freight_job))
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("create_sales_invoice"))
        frappe.throw(_("Error creating Sales Invoice: {0}").format(str(e)))


def get_income_account(expense_type):
    """Maps expense types to income accounts."""
    mapping = {
        "Freight": "Freight Income - FF",
        "Customs": "Customs Income - FF",
        "Handling": "Handling Income - FF",
        "Storage": "Storage Income - FF",
        "etc": "Other Income - FF"
    }

    account = mapping.get(expense_type, "Service Income - FF")

    # Verify account exists
    if not frappe.db.exists("Account", account):
        frappe.log_error(f"Account '{account}' not found for expense type '{expense_type}'", "get_income_account")
        return None

    return account


def get_default_cost_center():
    """Get default cost center or fallback."""
    cost_center = frappe.db.get_value("Company", "Main", "cost_center") or "Main - FF"
    return cost_center
