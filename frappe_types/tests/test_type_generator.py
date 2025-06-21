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
        shutil.rmtree(types_base_path)
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
        
    def test_generate_types_for_doctype(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_doctype(self.test_doctype_name)
        with open(types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(content.rstrip(), expected_ts_file.rstrip())
    
    def test_generate_types_for_module(self):
        generator = TypeGenerator(app_name="frappe_types")

        generator.generate_module(module)
        with open(types_output_path, "r") as f:
            content = f.read()
            self.assertEqual(content.rstrip(), expected_ts_file.rstrip())

expected_ts_file = """\

export interface TestGeneratedDocType{
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
	/**	Field 1 : Data	*/
	field_1?: string
	/**	Field 2 : Int	*/
	field_2?: number
}
"""
