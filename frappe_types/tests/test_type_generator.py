import frappe
from frappe.tests.utils import FrappeTestCase
from frappe_types.frappe_types.type_generator import TypeGenerator
import os
import shutil

module = "Frappe Types"
test_dir = os.path.dirname(__file__)
types_base_path = os.path.join(test_dir, 'types')
types_output_path = os.path.join(types_base_path, module.replace(" ", ""), 'TestGeneratedDocType.ts')

class TestTypeGenerator(FrappeTestCase):
    test_doctype_name = "Test Generated DocType"

    def tearDown(self) -> None:
        shutil.rmtree(types_base_path, ignore_errors=True)
        return super().tearDown()

    @classmethod
    def setUpClass(cls):
        frappe.delete_doc("DocType", cls.test_doctype_name, force=True, delete_permanently=True)

        doctype = frappe.new_doc("DocType")
        doctype.name = cls.test_doctype_name
        doctype.module = module
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.is_tree = 0
        doctype.is_virtual = 0

        dataField = {
                    "fieldname": "field_1",
                    "fieldtype": "Data",
                    "label": "Field 1",
                }
        intField = {
                    "fieldname": "field_2",
                    "fieldtype": "Int",
                    "label": "Field 2",
                }
        doctype.append("fields", dataField)
        doctype.append("fields", intField)
        doctype.append("permissions", {"role": "System Manager"})
        doctype.insert()

        frappe.db.delete("App Type Generation Paths")
        type_gen_doc = frappe.new_doc("Type Generation Settings")
        type_gen_doc.append("type_settings", {"app_name": "frappe_types", "app_path": "frappe_types/tests"})
        type_gen_doc.save()

        type_gen_settings = frappe.get_single("Type Generation Settings")
        type_gen_settings.include_custom_doctypes = 1
        type_gen_settings.save()
        
    def test_generate_types_for_doctype(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_doctype(self.test_doctype_name)
        with open(types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(default_fields))
    
    def test_generate_types_for_module(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_module(module)
        with open(types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(default_fields))

    def test_updates_types(self):
        doc = frappe.get_doc("DocType", self.test_doctype_name)
        doc.append("fields", {"fieldname": "field_3", "fieldtype": "Data", "label": "Field 3"})
        doc.save()

        with open(types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(sanitize_content(content), get_expected_ts_file(default_fields, updated_fields))

    def test_generation_paused(self):
        frappe.conf["frappe_types_pause_generation"] = 1
        generator = TypeGenerator(app_name="frappe_types")
        generator.generate_doctype(self.test_doctype_name)

        self.assertFalse(os.path.exists(types_output_path))

        frappe.conf.pop("frappe_types_pause_generation", None)


expected_template = """\
export interface TestGeneratedDocType{{
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
{fields}
}}
"""

default_fields = """\
	/**	Field 1 : Data	*/
	field_1?: string
	/**	Field 2 : Int	*/
	field_2?: number
"""

updated_fields = """\
	/**	Field 3 : Data	*/
	field_3?: string
"""

def sanitize_content(text: str) -> str:
    tabsize = 4
    spaces = " " * tabsize
    cleaned_lines = [
        # tabs → spaces, trim right-side blanks
        line.replace("\t", spaces).rstrip()          
        for line in text.splitlines()
        # drop empty / whitespace-only lines
        if line.strip()                             
    ]
    return "\n".join(cleaned_lines).rstrip()

def get_expected_ts_file(*fields: str) -> str:
    concatenated_fields = "\n".join(fields)
    formatted = expected_template.format(fields=concatenated_fields)
    return sanitize_content(formatted)
