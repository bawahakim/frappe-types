// Copyright (c) 2022, Nikhil Kothari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Type Generation Settings", {
	refresh: async function (frm) {
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

		const { message: apps_json } = await frappe.call(
			"frappe.core.doctype.module_def.module_def.get_installed_apps"
		);
		const apps = JSON.parse(apps_json);

		const app_name_field = frm.fields_dict.type_settings.grid.get_docfield("app_name");
		const rows = frm.doc.type_settings;
		const filtered_apps = apps.filter((app) => !rows.find((row) => row.app_name === app));
		app_name_field.options = filtered_apps;
	},
});
