context("Type Generation Settings", () => {
	beforeEach(() => {
		cy.login("Administrator", "admin");
		cy.visit("/desk");
		cy.call("frappe.client.set_value", {
			doctype: "Type Generation Settings",
			name: "Type Generation Settings",
			fieldname: "type_settings",
			value: [],
		});
		cy.call("frappe.client.save", {
			doc: {
				doctype: "Type Generation Settings",
				export_to_root: 0,
			},
		});
	});

	it("saves a new type generation setting", () => {
		cy.visit("/app/type-generation-settings");
		click_add_row();
		click_row(1);

		select_app_name("frappe");
		cy.fill_field("app_path", "src");

		cy.save();
	});

	it("prevents saving when app_path is empty", () => {
		cy.visit("/app/type-generation-settings");
		click_add_row();
		click_row(1);

		select_app_name("frappe");

		save();

		cy.findByText(/app path is required/i);
	});

	it("allows no app_path if export to root is checked", () => {
		cy.visit("/app/type-generation-settings");
		cy.fill_field("export_to_root", 1);
		click_add_row();

		click_row(1);

		select_app_name("frappe");

		cy.save();
	});

	it("generates all types when there is at least one app", () => {
		cy.visit("/app/type-generation-settings");
		click_add_row();
		click_row(1);
		select_app_name("frappe");
		cy.fill_field("app_path", "src");
		cy.save();
		cy.intercept(
			"POST",
			"/api/method/frappe_types.frappe_types.type_generator.export_all_apps"
		).as("generate_all");
		cy.findByRole("button", { name: /generate all/i }).click();
		cy.wait("@generate_all");
		cy.findByText(/success/i);
	});
});

const click_add_row = () => {
	cy.findByRole("button", { name: /add row/i }).click();
};

const click_row = (row_idx) => {
	cy.get('.frappe-control[data-fieldname="type_settings"] [data-idx="1"]').as("row1");
	cy.get("@row1").find(".btn-open-row").click();
};

const select_app_name = (app_name) => {
	cy.get("@row1").find('[data-fieldname="app_name"] select').as("app_name");
	cy.get("@app_name").select(app_name);
};

const save = () => {
	cy.findByRole("button", { name: /save/i }).click({ force: true });
};
