import os
import shutil

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_types.frappe_types.type_generator import TypeGenerator
from frappe_types.tests.utils import TestTypeGeneratorUtils, sanitize_content, to_ts_type
from pathlib import Path

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

	def instantiate_type_generator(
		self, app_name: str = TestTypeGeneratorUtils.app_name, generate_child_tables: bool = False
	) -> TypeGenerator:
		return TypeGenerator(app_name=app_name, generate_child_tables=generate_child_tables)

	def setUp(self) -> None:
		TestTypeGeneratorUtils.setup()
		return super().setUp()

	def tearDown(self) -> None:
		TestTypeGeneratorUtils.cleanup()
		return super().tearDown()

	@classmethod
	def tearDownClass(cls) -> None:
		TestTypeGeneratorUtils.cleanup()
		return super().tearDownClass()

	def test_generate_types_for_doctype(self):
		generator = self.instantiate_type_generator()

		generator.generate_doctype(self.doctype_name)

		for file_path in TestTypeGeneratorUtils.get_types_module_files_paths():
			self.assertFalse(os.path.exists(file_path))

		for file_path in TestTypeGeneratorUtils.get_app_2_output_file_paths():
			self.assertFalse(os.path.exists(file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=False),
			)

		self._assert_doctype_map(
			Path(TestTypeGeneratorUtils.get_types_output_base_path()) / "DocTypeMap.d.ts",
			[
				TestTypeGeneratorUtils.test_doctype_name,
			],
		)

	def test_generate_types_for_doctype_with_child_table(self):
		generator = self.instantiate_type_generator(generate_child_tables=True)

		generator.generate_doctype(self.doctype_name)

		self.assertTrue(os.path.exists(self.child_table_typescript_file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=True),
			)

	def test_generate_types_for_module(self):
		generator = self.instantiate_type_generator()

		generator.generate_module(TestTypeGeneratorUtils.module)

		for file_path in TestTypeGeneratorUtils.get_types_module_files_paths():
			self.assertTrue(os.path.exists(file_path))

		for file_path in TestTypeGeneratorUtils.get_app_2_output_file_paths():
			self.assertFalse(os.path.exists(file_path))

		self.assertTrue(os.path.exists(self.child_table_typescript_file_path))

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content),
				TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=True),
			)

		self._assert_doctype_map(
			Path(TestTypeGeneratorUtils.get_types_output_base_path()) / "DocTypeMap.d.ts",
			[
				TestTypeGeneratorUtils.test_doctype_name,
				TestTypeGeneratorUtils.test_doctype_name_2,
			],
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
		generator = self.instantiate_type_generator()
		generator.generate_doctype(self.doctype_name)

		self.assertFalse(os.path.exists(self.generated_typescript_file_path))

	def test_export_to_root(self):
		settings = frappe.get_single("Type Generation Settings")
		settings.export_to_root = 1
		settings.root_output_path = "types"
		settings.save()

		generator = self.instantiate_type_generator()
		generator.generate_doctype(self.doctype_name)

		with open(self.generated_typescript_file_path) as f:
			content = f.read()
			self.assertEqual(
				sanitize_content(content), TestTypeGeneratorUtils.get_expected_ts_file(with_child_table=False)
			)

		self._assert_doctype_map(
			Path(TestTypeGeneratorUtils.temp_dir) / "types" / "DocTypeMap.d.ts",
			[
				TestTypeGeneratorUtils.test_doctype_name,
			],
		)

	def test_export_all_apps(self):
		generator = TypeGenerator(app_name="")
		generator.export_all_apps()

		for file_path in TestTypeGeneratorUtils.get_all_apps_output_file_paths():
			self.assertTrue(os.path.exists(file_path))

		map_path_1 = Path(TestTypeGeneratorUtils.get_types_output_base_path()) / "DocTypeMap.d.ts"
		self._assert_doctype_map(
			map_path_1,
			[
				TestTypeGeneratorUtils.test_doctype_name_2,
				TestTypeGeneratorUtils.test_doctype_name,
				TestTypeGeneratorUtils.doctype_child_name,
			],
		)

		map_path_2 = Path(TestTypeGeneratorUtils.get_types_output_base_path(TestTypeGeneratorUtils.app_name_2)) / "DocTypeMap.d.ts"
		self._assert_doctype_map(
			map_path_2,
			[
				TestTypeGeneratorUtils.test_doctype_name_3,
			],
			TestTypeGeneratorUtils.module_2,
		)

	def test_export_all_apps_to_root(self):
		settings = frappe.get_single("Type Generation Settings")
		settings.export_to_root = 1
		settings.root_output_path = "types"
		settings.save()

		generator = TypeGenerator(app_name="")
		generator.export_all_apps()

		for file_path in TestTypeGeneratorUtils.get_all_apps_output_file_paths():
			self.assertTrue(os.path.exists(file_path))

		map_path = Path(TestTypeGeneratorUtils.temp_dir) / "types" / "DocTypeMap.d.ts"
		self._assert_doctype_map(
			map_path,
			[
				TestTypeGeneratorUtils.test_doctype_name_2,
				TestTypeGeneratorUtils.test_doctype_name,
				TestTypeGeneratorUtils.doctype_child_name,
			],
		)
		self._assert_doctype_map(
			map_path,
			[
				TestTypeGeneratorUtils.test_doctype_name_3,
			],
			TestTypeGeneratorUtils.module_2,
		)

	def _assert_doctype_map(
		self, map_path: Path, doctypes: list[str], module: str = TestTypeGeneratorUtils.module
	):
		self.assertTrue(map_path.exists())
		content = sanitize_content(map_path.read_text())
		self.assertIn("declare global {\n  interface DocTypeMap {", content)
		for orig in doctypes:
			ts = to_ts_type(orig)
			module_dir = to_ts_type(module)
			expected_mapping = f'"{orig}": {ts};'
			self.assertIn(expected_mapping, content)
			expected_import = f"import {{ {ts} }} from './{module_dir}/{ts}';"
			self.assertIn(expected_import, content)
		self.assertIn("export {};", content)
