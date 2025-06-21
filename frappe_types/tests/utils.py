import os

import frappe
from frappe.core.doctype.doctype.doctype import DocType

class TestTypeGeneratorUtils:
    module = "Frappe Types"
    test_doctype_name = "Test Generated DocType"
    doctype_child_name = f"{test_doctype_name} Child Table"

    test_dir = os.path.dirname(__file__)
    types_base_path = os.path.join(test_dir, 'types')
    types_output_path = os.path.join(types_base_path, module.replace(" ", ""), 'TestGeneratedDocType.ts')

    @classmethod
    def generate_test_doctype(cls):
        cls._generate_test_doctype_child_table()

        doctype: DocType = frappe.new_doc("DocType")
        doctype.name = cls.test_doctype_name
        doctype.module = cls.module
        doctype.custom = 1

        # Core field templates covering most field types supported by TypeGenerator
        field_defs = [
            {"fieldname": "data_field", "fieldtype": "Data", "label": "Data Field"},
            {"fieldname": "int_field", "fieldtype": "Int", "label": "Int Field"},
            {"fieldname": "link_field", "fieldtype": "Link", "label": "Link Field", "options": "DocType"},
            {"fieldname": "dynamic_link_field", "fieldtype": "Dynamic Link", "label": "Dynamic Link Field", "options": "link_field"},
            {"fieldname": "read_only_field", "fieldtype": "Read Only", "label": "Read Only Field"},
            {"fieldname": "password_field", "fieldtype": "Password", "label": "Password Field"},
            {"fieldname": "check_field", "fieldtype": "Check", "label": "Check Field"},
            {"fieldname": "float_field", "fieldtype": "Float", "label": "Float Field"},
            {"fieldname": "currency_field", "fieldtype": "Currency", "label": "Currency Field"},
            {"fieldname": "percent_field", "fieldtype": "Percent", "label": "Percent Field"},
            {"fieldname": "attach_field", "fieldtype": "Attach", "label": "Attach Field"},
            {"fieldname": "attach_image_field", "fieldtype": "Attach Image", "label": "Attach Image Field"},
            {"fieldname": "image_field", "fieldtype": "Image", "label": "Image Field"},
            {"fieldname": "code_field", "fieldtype": "Code", "label": "Code Field"},
            {"fieldname": "long_text_field", "fieldtype": "Long Text", "label": "Long Text Field"},
            {"fieldname": "small_text_field", "fieldtype": "Small Text", "label": "Small Text Field"},
            {"fieldname": "text_field", "fieldtype": "Text", "label": "Text Field"},
            {"fieldname": "text_editor_field", "fieldtype": "Text Editor", "label": "Text Editor Field"},
            {"fieldname": "markdown_field", "fieldtype": "Markdown Editor", "label": "Markdown Field"},
            {"fieldname": "date_field", "fieldtype": "Date", "label": "Date Field"},
            {"fieldname": "datetime_field", "fieldtype": "Datetime", "label": "Datetime Field"},
            {"fieldname": "time_field", "fieldtype": "Time", "label": "Time Field"},
            {"fieldname": "phone_field", "fieldtype": "Phone", "label": "Phone Field"},
            {"fieldname": "color_field", "fieldtype": "Color", "label": "Color Field"},
            {"fieldname": "duration_field", "fieldtype": "Duration", "label": "Duration Field"},
            {"fieldname": "select_field", "fieldtype": "Select", "label": "Select Field", "options": "Option 1\nOption 2"},
            {"fieldname": "table_field", "fieldtype": "Table", "label": "Table Field", "options": cls.doctype_child_name},
        ]

        for f in field_defs:
            doctype.append("fields", f)

        doctype.append("permissions", {"role": "System Manager"})
        doctype.insert()
    
    @classmethod
    def cleanup_db(cls):
        frappe.delete_doc("DocType", cls.test_doctype_name, force=True, delete_permanently=True)
        frappe.delete_doc("DocType", cls.doctype_child_name, force=True, delete_permanently=True)
        frappe.db.delete("App Type Generation Paths")

    @classmethod
    def _generate_test_doctype_child_table(cls):
        doctype: DocType = frappe.new_doc("DocType")
        doctype.name = cls.doctype_child_name
        doctype.module = cls.module
        doctype.custom = 1
        doctype.istable = 1

        field_defs = [
            {"fieldname": "data_field", "fieldtype": "Data", "label": "Data Field"},
            {"fieldname": "int_field", "fieldtype": "Int", "label": "Int Field"},
        ]

        for f in field_defs:
            doctype.append("fields", f)

        doctype.append("permissions", {"role": "System Manager"})
        doctype.insert()

expected_template = """\
{import_child_table}
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
	/**	Data Field : Data	*/
	data_field?: string
	/**	Int Field : Int	*/
	int_field?: number
	/**	Link Field : Link - DocType	*/
	link_field?: string
	/**	Dynamic Link Field : Dynamic Link	*/
	dynamic_link_field?: string
	/**	Read Only Field : Read Only	*/
	read_only_field?: string
	/**	Password Field : Password	*/
	password_field?: string
	/**	Check Field : Check	*/
	check_field?: 0 | 1
	/**	Float Field : Float	*/
	float_field?: number
	/**	Currency Field : Currency	*/
	currency_field?: number
	/**	Percent Field : Percent	*/
	percent_field?: number
	/**	Attach Field : Attach	*/
	attach_field?: string
	/**	Attach Image Field : Attach Image	*/
	attach_image_field?: string
	/**	Image Field : Image	*/
	image_field?: string
	/**	Code Field : Code	*/
	code_field?: string
	/**	Long Text Field : Long Text	*/
	long_text_field?: string
	/**	Small Text Field : Small Text	*/
	small_text_field?: string
	/**	Text Field : Text	*/
	text_field?: string
	/**	Text Editor Field : Text Editor	*/
	text_editor_field?: string
	/**	Markdown Field : Markdown Editor	*/
	markdown_field?: string
	/**	Date Field : Date	*/
	date_field?: string
	/**	Datetime Field : Datetime	*/
	datetime_field?: string
	/**	Time Field : Time	*/
	time_field?: string
	/**	Phone Field : Phone	*/
	phone_field?: string
	/**	Color Field : Color	*/
	color_field?: string
	/**	Duration Field : Duration	*/
	duration_field?: string
	/**	Select Field : Select	*/
	select_field?: "Option 1" | "Option 2"
"""

updated_fields = """\
    /**	Data Field New : Data	*/
    data_field_new?: string
"""

table_field_linked = """\
    /**	Table Field : Table - Test Generated DocType Child Table	*/
    table_field?: TestGeneratedDocTypeChildTable[]
"""

table_field_any = """\
    /**	Table Field : Table - Test Generated DocType Child Table	*/
    table_field?: any
"""

import_child_table = """\
import { TestGeneratedDocTypeChildTable } from './TestGeneratedDocTypeChildTable'
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

def get_expected_ts_file(with_child_table: bool = False, with_updated_fields: bool = False) -> str:
    fields = [default_fields]

    if with_child_table:
        fields.append(table_field_linked)
    else:
        fields.append(table_field_any)
    
    if with_updated_fields:
        fields.append(updated_fields)

    formatted = expected_template.format(fields="\n".join(fields), import_child_table=import_child_table if with_child_table else "")
    return sanitize_content(formatted)
