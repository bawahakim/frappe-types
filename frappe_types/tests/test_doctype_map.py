import os

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_types.frappe_types.type_generator import TypeGenerator
from frappe_types.frappe_types.utils import to_ts_type
from frappe_types.tests.utils import TestTypeGeneratorUtils, sanitize_content


class TestDocTypeMap(FrappeTestCase):
	def setUp(self):
		TestTypeGeneratorUtils.setup()
		super().setUp()

	def tearDown(self):
		TestTypeGeneratorUtils.cleanup()
		super().tearDown()

	@classmethod
	def tearDownClass(cls):
		TestTypeGeneratorUtils.cleanup()
		super().tearDownClass()

	def test_write_doctype_map(self):
		generator = TypeGenerator(app_name=TestTypeGeneratorUtils.app_name, generate_child_tables=True)
		generator.generate_module(TestTypeGeneratorUtils.module)
		generator.write_doctype_map()
		map_path = os.path.join(TestTypeGeneratorUtils.get_types_output_base_path(), "DocTypeMap.ts")
		self.assertTrue(os.path.exists(map_path))
		content = sanitize_content(open(map_path).read())
		self.assertIn("export type DocTypeMap = {", content)
		for orig in [
			TestTypeGeneratorUtils.test_doctype_name,
			TestTypeGeneratorUtils.test_doctype_name_2,
			TestTypeGeneratorUtils.doctype_child_name,
		]:
			ts = to_ts_type(orig)
			module_dir = to_ts_type(TestTypeGeneratorUtils.module)
			expected_mapping = f'"{orig}": {ts};'
			self.assertIn(expected_mapping, content)
			expected_import = f"import {{ {ts} }} from './{module_dir}/{ts}';"
			self.assertIn(expected_import, content)

	def test_write_doctype_map_export_to_root(self):
		# enable export to root
		settings = frappe.get_single("Type Generation Settings")
		settings.export_to_root = 1
		settings.root_output_path = "types"
		settings.save()
		generator = TypeGenerator(app_name=TestTypeGeneratorUtils.app_name, generate_child_tables=True)
		generator.generate_module(TestTypeGeneratorUtils.module)
		generator.write_doctype_map()
		map_path = os.path.join(TestTypeGeneratorUtils.temp_dir, "types", "DocTypeMap.ts")
		self.assertTrue(os.path.exists(map_path))
		content = sanitize_content(open(map_path).read())
		self.assertIn("export type DocTypeMap = {", content)
		for orig in [
			TestTypeGeneratorUtils.test_doctype_name,
			TestTypeGeneratorUtils.test_doctype_name_2,
			TestTypeGeneratorUtils.doctype_child_name,
		]:
			ts = to_ts_type(orig)
			module_dir = to_ts_type(TestTypeGeneratorUtils.module)
			expected_mapping = f'"{orig}": {ts};'
			self.assertIn(expected_mapping, content)
			expected_import = f"import {{ {ts} }} from './{module_dir}/{ts}';"
			self.assertIn(expected_import, content)
