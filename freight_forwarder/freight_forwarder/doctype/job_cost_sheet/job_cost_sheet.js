// Copyright (c) 2026, Ahmad Raza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Cost Sheet", {
	refresh(frm) {
		// Add button to create purchase invoices
		if (frm.doc.docstatus === 1 && !frm.doc.purchase_invoice_created) {
			frm.add_custom_button("Create Purchase Invoice", function() {
				frappe.call({
					method: "freight_forwarder.purchase_invoice.create_purchase_invoice",
					args: {
						job_cost_sheet: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							const invoices = r.message.invoices || [];
							frappe.msgprint({
								title: "Purchase Invoices Created",
								indicator: "green",
								message: invoices.map(inv => 
									`<a href="#Form/Purchase Invoice/${inv}">${inv}</a>`
								).join("<br>")
							});
							
							// Open first invoice
							if (invoices.length > 0) {
								frappe.set_route("Form", "Purchase Invoice", invoices[0]);
							}
							
							// Refresh current form
							frm.reload_doc();
						}
					}
				});
			});
		}
	},
});
