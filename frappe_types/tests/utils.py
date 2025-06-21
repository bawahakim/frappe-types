import frappe

def generate_test_doctype(test_doctype_name, module):
    doctype = frappe.new_doc("DocType")
    doctype.name = test_doctype_name
    doctype.module = module
    doctype.custom = 1
    doctype.is_submittable = 0
    doctype.is_tree = 0
    doctype.is_virtual = 0

    dataField = {
                "fieldname": "data_field",
                "fieldtype": "Data",
                "label": "Data Field",
            }
    intField = {
                "fieldname": "int_field",
                "fieldtype": "Int",
                "label": "Int Field",
            }
    doctype.append("fields", dataField)
    doctype.append("fields", intField)
    doctype.append("permissions", {"role": "System Manager"})
    doctype.insert()