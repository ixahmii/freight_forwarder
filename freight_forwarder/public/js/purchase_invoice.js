frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        // Add button to go to Freight Job if freight_job field exists
        if (frm.doc.freight_job) {
            frm.add_custom_button("Go to Freight Job", function() {
                frappe.set_route("Form", "Freight Job", frm.doc.freight_job);
            }, "Actions");
        }
    }
});
