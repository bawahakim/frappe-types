// Copyright (c) 2022, Nikhil Kothari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Type Generation Settings", {
	setup: function (frm) {
		filter_apps_dropdown(frm);
	},
	refresh: async function (frm) {
		// Toggle root output path field
		frm.toggle_enable("root_output_path", frm.doc.export_to_root);

		update_app_path_visibility(frm);

		create_generate_all_button(frm);
	},
	export_to_root: function (frm) {
		update_app_path_visibility(frm);
	},
	validate: function (frm) {
		update_app_path_visibility(frm);

		if (!frm.doc.export_to_root) {
			frm.doc.type_settings.forEach((row) => {
				if (!row.app_path) {
					frappe.throw(
						`Row ${row.idx}: App Path is required when Export to Root is disabled`
					);
				}
			});
		}
	},
});

const update_app_path_visibility = (frm) => {
	const type_setting_field = frm.fields_dict["type_settings"];

	const { grid } = type_setting_field;

	if (!grid) return;

	grid.toggle_reqd("app_path", !frm.doc.export_to_root);
	grid.toggle_enable("app_path", !frm.doc.export_to_root);
};

const filter_apps_dropdown = async (frm, cdt, cdn) => {
	const { message: apps_json } = await frappe.call(
		"frappe.core.doctype.module_def.module_def.get_installed_apps"
	);
	const apps = JSON.parse(apps_json);

	const { grid } = frm.fields_dict.type_settings;
	grid.update_docfield_property("app_name", "options", apps);
};

const create_generate_all_button = (frm) => {
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
};
