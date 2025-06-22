import os
import shutil

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_types.frappe_types.type_generator import TypeGenerator
from frappe_types.tests.utils import TestTypeGeneratorUtils, sanitize_content


class TestTypeGenerator(FrappeTestCase):
	@property
	def types_module_path(self) -> str:
		return TestTypeGeneratorUtils.get_types_module_path()

	@property
	def generated_typescript_file_path(self) -> str:
		return TestTypeGeneratorUtils.get_generated_typescript_file_path()

	@property
	def child_table_typescript_file_path(self) -> str:
		return TestTypeGeneratorUtils.get_child_table_typescript_file_path()

	@property
	def doctype_name(self) -> str:
		return TestTypeGeneratorUtils.test_doctype_name

	def tearDown(self) -> None:
		frappe.conf.pop("frappe_types_pause_generation", None)
		shutil.rmtree(self.types_module_path, ignore_errors=True)
		return super().tearDown()

	@classmethod
	def setUpClass(cls):
		TestTypeGeneratorUtils.cleanup_db()
		TestTypeGeneratorUtils.generate_test_doctype()

		type_gen_doc = frappe.new_doc("Type Generation Settings")
		type_gen_doc.append(
			"type_settings",
			{"app_name": "frappe_types", "app_path": "frappe_types/tests"},
		)
		type_gen_doc.save()

		type_gen_settings = frappe.get_single("Type Generation Settings")
		type_gen_settings.include_custom_doctypes = 1
		type_gen_settings.save()

	def test_generate_types_for_doctype(self):
		generator = TypeGenerator(app_name="frappe_types")

		generator.generate_doctype(self.doctype_name)

		for file_path in TestTypeGeneratorUtils.get_types_module_files_paths():
			self.assertFalse(os.path.exists(file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=False),
			)

	def test_generate_types_for_doctype_with_child_table(self):
		generator = TypeGenerator(app_name="frappe_types", generate_child_tables=True)

		generator.generate_doctype(self.doctype_name)

		self.assertTrue(os.path.exists(self.child_table_typescript_file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=True),
			)

	def test_generate_types_for_module(self):
		generator = TypeGenerator(app_name="frappe_types")

		generator.generate_module(TestTypeGeneratorUtils.module)

		for file_path in TestTypeGeneratorUtils.get_types_module_files_paths():
			self.assertTrue(os.path.exists(file_path))

		self.assertTrue(os.path.exists(self.child_table_typescript_file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=True),
			)

	def test_updates_types(self):
		doc = frappe.get_doc("DocType", self.doctype_name)
		doc.append(
			"fields",
			{
				"fieldname": "data_field_new",
				"fieldtype": "Data",
				"label": "Data Field New",
			},
		)
		doc.save()

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_updated_fields=True),
			)

	def test_generation_paused(self):
		frappe.conf["frappe_types_pause_generation"] = 1
		generator = TypeGenerator(app_name="frappe_types")
		generator.generate_doctype(self.doctype_name)

		self.assertFalse(os.path.exists(self.generated_typescript_file_path))
