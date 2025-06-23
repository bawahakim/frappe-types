// Copyright (c) 2022, Nikhil Kothari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Type Generation Settings", {
	refresh: function (frm) {
		// Toggle root output path field
		frm.toggle_enable("root_output_path", frm.doc.export_to_root);
		// Toggle app_path field in type_settings child table
		if (frm.fields_dict["type_settings"]) {
			frm.fields_dict["type_settings"].grid.toggle_enable(
				"app_path",
				!frm.doc.export_to_root
			);
		}

		frm.add_custom_button("Generate All", function () {
			frappe.call({
				method: "frappe_types.frappe_types.type_generator.export_all_apps",
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({
							title: "Success",
							message: r.message,
							indicator: "green",
						});
					}
				},
			});
		});
	},
});
