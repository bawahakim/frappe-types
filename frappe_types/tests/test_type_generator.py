import frappe
from frappe.tests.utils import FrappeTestCase
from frappe_types.frappe_types.type_generator import TypeGenerator
import os
import shutil
from frappe_types.tests.utils import TestTypeGeneratorUtils, sanitize_content, get_expected_ts_file, default_fields, updated_fields

class TestTypeGenerator(FrappeTestCase):
    def tearDown(self) -> None:
        frappe.conf.pop("frappe_types_pause_generation", None)
        shutil.rmtree(TestTypeGeneratorUtils.types_base_path, ignore_errors=True)
        return super().tearDown()

    @classmethod
    def setUpClass(cls):
        TestTypeGeneratorUtils.cleanup_db()
        TestTypeGeneratorUtils.generate_test_doctype()

        type_gen_doc = frappe.new_doc("Type Generation Settings")
        type_gen_doc.append("type_settings", {"app_name": "frappe_types", "app_path": "frappe_types/tests"})
        type_gen_doc.save()

        type_gen_settings = frappe.get_single("Type Generation Settings")
        type_gen_settings.include_custom_doctypes = 1
        type_gen_settings.save()
        
    def test_generate_types_for_doctype(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_doctype(TestTypeGeneratorUtils.test_doctype_name)
        with open(TestTypeGeneratorUtils.types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(with_child_table=False))

    def test_generate_types_for_doctype_with_child_table(self):
        generator = TypeGenerator(app_name="frappe_types", generate_child_tables=True)

        generator.generate_doctype(TestTypeGeneratorUtils.test_doctype_name)
        with open(TestTypeGeneratorUtils.types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(with_child_table=True))
    
    def test_generate_types_for_module(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_module(TestTypeGeneratorUtils.module)
        with open(TestTypeGeneratorUtils.types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(with_child_table=True))

    def test_updates_types(self):
        doc = frappe.get_doc("DocType", TestTypeGeneratorUtils.test_doctype_name)
        doc.append("fields", {"fieldname": "data_field_new", "fieldtype": "Data", "label": "Data Field New"})
        doc.save()

        with open(TestTypeGeneratorUtils.types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(with_updated_fields=True))

    def test_generation_paused(self):
        frappe.conf["frappe_types_pause_generation"] = 1
        generator = TypeGenerator(app_name="frappe_types")
        generator.generate_doctype(TestTypeGeneratorUtils.test_doctype_name)

        self.assertFalse(os.path.exists(TestTypeGeneratorUtils.types_output_path))

