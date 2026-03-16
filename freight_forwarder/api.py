import frappe
from frappe.utils import flt

def update_job_profitability(doc, method=None):
    """
    Triggered from Sales/Purchase Invoice hooks.
    Calculates profitability using direct SQL for aggregation.
    """
    job_id = doc.get("freight_job")

    if not job_id:
        return

    # 1. Sum Revenue from Sales Invoices
    # We use frappe.db.sql to perform the calculation directly in the database
    total_revenue = frappe.db.sql("""
        SELECT SUM(base_net_total)
        FROM `tabSales Invoice`
        WHERE freight_job = %s AND docstatus = 1
    """, (job_id,))[0][0] or 0

    # 2. Sum Cost from Purchase Invoices
    total_cost = frappe.db.sql("""
        SELECT SUM(base_net_total)
        FROM `tabPurchase Invoice`
        WHERE freight_job = %s AND docstatus = 1
    """, (job_id,))[0][0] or 0

    # 3. Calculate Margins
    gross_profit = flt(total_revenue) - flt(total_cost)
    gp_percent = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

    # 4. Update the Freight Job
    frappe.db.set_value("Freight Job", job_id, {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "gp_": gp_percent
    }, update_modified=True)

    # Clear cache to ensure UI reflects changes
    frappe.clear_document_cache("Freight Job", job_id)
