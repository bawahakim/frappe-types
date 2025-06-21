import frappe
from pathlib import Path
from typing import Optional
from .utils import create_file, is_developer_mode_enabled
import subprocess

class TypeGenerator:
    """High-level convenience wrapper around the module-level helper functions
    for generating TypeScript type files.  This allows callers (and tests)
    to configure the generator once via ``__init__`` and then reuse the same
    instance for multiple DocTypes / modules.

    Parameters
    ----------
    app_name: str
        Name of the Frappe app the DocTypes belong to. Corresponds to the
        ``app_name`` argument previously passed to the standalone helper
        functions.
    generate_child_tables: bool, default False
        Whether to recursively generate type definitions for child table
        DocTypes encountered while processing the given DocType / module.
    custom_fields: bool, default False
        When *True* the generator will include custom fields together with
        standard ones (mirrors the `custom_fields` parameter of
        :func:`generate_types_for_doctype`).
    """

    def __init__(self, app_name: str, *, generate_child_tables: bool = False, custom_fields: bool = False) -> None:
        self.app_name = app_name
        self.generate_child_tables = generate_child_tables
        self.custom_fields = custom_fields

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate_doctype(self, doctype: str):
        """Generate a `.ts` type definition file for a single DocType."""
        try:
            # custom_fields True means that the generate .ts file for custom fields with original fields
            doc = frappe.get_meta(doctype) if self.custom_fields else frappe.get_doc(
                'DocType', doctype)

            # Check if type generation is paused
            if self._is_generation_paused():
                print("Frappe Types is paused")
                return

            if is_developer_mode_enabled() and self._is_valid_doctype(doc):
                print("Generating type definition file for " + doc.name)
                module_name = doc.module

                module_path = self._get_module_path(self.app_name, module_name)
                if module_path:
                    self._generate_type_definition_file(doc, module_path)
                
        except Exception as e:
            err_msg = f": {str(e)}\n{frappe.get_traceback()}"
            print(
                f"An error occurred while generating type for {doctype} {err_msg}")

    def generate_module(self, module: str):
        """Generate type definition files for *all* DocTypes inside *module*."""
        try:
            child_tables = [doctype['name'] for doctype in frappe.get_list(
                'DocType', filters={'module': module, 'istable': 1})]
            if len(child_tables) > 0:
                for child_table in child_tables:
                    self.generate_doctype(child_table)

            doctypes = [doctype['name'] for doctype in frappe.get_list(
                'DocType', filters={'module': module, 'istable': 0})]

            if len(doctypes) > 0:
                for doctype in doctypes:
                    self.generate_doctype(doctype)
        except Exception as e:
            err_msg = f": {str(e)}\n{frappe.get_traceback()}"
            print(
                f"An error occurred while generating type for {module} {err_msg}")
    
    def create_type_definition_file(self, doc):
        # Check if type generation is paused
        if self._is_generation_paused():
            print("Frappe Types is paused")
            return
    
        if frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_setup_wizard:
            print("Skipping type generation in patch, migrate, install or setup wizard")
            return

        doctype = doc

        if is_developer_mode_enabled() and self._is_valid_doctype(doctype):
            print("Generating type definition file for " + doctype.name)
            module_name = doctype.module
            app_name = frappe.db.get_value('Module Def', module_name, 'app_name')

            module_path = self._get_module_path(app_name, module_name)
            if module_path:
                self._generate_type_definition_file(doctype, module_path)


    # ---------------------------------------------------------------------
    # Private methods
    # ---------------------------------------------------------------------
    def _is_generation_paused(self) -> bool:
        """Return True if type generation has been temporarily disabled via
        the `frappe_types_pause_generation` flag in *common_site_config*."""
        is_paused_config = frappe.get_conf().get("frappe_types_pause_generation", 0)
        return bool(is_paused_config)

    def _get_module_path(self, app_name: str, module_name: str) -> Optional[Path]:
        """Return the directory `<app>/<custom path>/types/<Module>` creating any
        missing directories along the way.  Returns *None* when the DocType
        should be ignored (e.g. core apps, unconfigured app, or missing app
        path)."""
        # Ignore core apps
        if app_name in {"frappe", "erpnext"}:
            print("Ignoring core app DocTypes")
            return None

        app_path = Path("../apps") / app_name
        if not app_path.exists():
            print("App path does not exist - ignoring type generation")
            return None

        # Look-up path in Type Generation Settings
        type_generation_settings = frappe.get_doc('Type Generation Settings').as_dict().type_settings
        type_setting = next((ts for ts in type_generation_settings if ts.app_name == app_name), None)
        if not type_setting:
            return None

        # Ensure directories exist
        type_path: Path = app_path / type_setting.app_path / "types"
        type_path.mkdir(parents=True, exist_ok=True)

        module_path: Path = type_path / module_name.replace(" ", "")
        module_path.mkdir(exist_ok=True)
        return module_path

    def _generate_type_definition_file(self, doctype, module_path):

        doctype_name = doctype.name.replace(" ", "")
        type_file_path = module_path / (doctype_name + ".ts")
        type_file_content = self._generate_type_definition_content(
            doctype, module_path)

        create_file(type_file_path, type_file_content)


    def _generate_type_definition_content(self, doctype, module_path):
        import_statement = ""

        content = "export interface " + doctype.name.replace(" ", "") + "{\n"

        # Boilerplate types for all documents
        name_field_type = "string"
        if doctype.naming_rule == "Autoincrement":
            name_field_type = "number"
        content += f"\tname: {name_field_type}\n\tcreation: string\n\tmodified: string\n\towner: string\n\tmodified_by: string\n\tdocstatus: 0 | 1 | 2\n\tparent?: string\n\tparentfield?: string\n\tparenttype?: string\n\tidx?: number\n"

        for field in doctype.fields:
            if field.fieldtype in ["Section Break", "Column Break", "HTML", "Button", "Fold", "Heading", "Tab Break", "Break"]:
                continue
            content += self._get_field_comment(field)

            file_defination, statement = self._get_field_type_definition(
                field, doctype, module_path)

            if statement and import_statement.find(statement) == -1:
                import_statement += statement
            
            content += "\t" + file_defination + "\n"

        content += "}"

        return import_statement + "\n" + content

    def _get_field_comment(self, field):
        desc = field.description
        if field.fieldtype in ["Link", "Table", "Table MultiSelect"]:
            desc = field.options + \
                (" - " + field.description if field.description else "")
        return "\t/**\t" + (field.label if field.label else '') + " : " + field.fieldtype + ((" - " + desc) if desc else "") + "\t*/\n"


    def _get_field_type_definition(self, field, doctype, module_path):
        field_type,import_statement =  self._get_field_type(field, doctype, module_path)
        return field.fieldname + self._get_required(field) + ": " + field_type , import_statement


    def _get_field_type(self, field, doctype, module_path):

        basic_fieldtypes = {
            "Data": "string",
            "Small Text": "string",
            "Text Editor": "string",
            "Text": "string",
            "Code": "string",
            "Link": "string",
            "Dynamic Link": "string",
            "Read Only": "string",
            "Password": "string",
            "Text Editor": "string",
            "Check": "0 | 1",
            "Int": "number",
            "Float": "number",
            "Currency": "number",
            "Percent": "number",
            "Attach Image": "string",
            "Attach": "string",
            "HTML Editor": "string",
            "Image": "string",
            "Duration": "string",
            "Small Text": "string",
            "Date": "string",
            "Datetime": "string",
            "Time": "string",
            "Phone": "string",
            "Color": "string",
            "Long Text": "string",
            "Markdown Editor": "string",
        }

        if field.fieldtype in ["Table", "Table MultiSelect"]:
            return self._get_imports_for_table_fields(field, doctype, module_path)

        if field.fieldtype == "Select":
            if (field.options):
                options = field.options.split("\n")
                t = ""
                for option in options:
                    t += "\"" + option + "\" | "
                if t.endswith(" | "):
                    t = t[:-3]
                return t, None
            else:
                return 'string',None

        if field.fieldtype in basic_fieldtypes:
            return basic_fieldtypes[field.fieldtype], None
        else:
            return "any", None


    def _get_imports_for_table_fields(self, field, doctype, module_path):
        if field.fieldtype == "Table" or field.fieldtype == "Table MultiSelect":
            doctype_module_name = doctype.module
            table_doc = frappe.get_doc('DocType', field.options)
            table_module_name = table_doc.module
            should_import = False
            import_statement = ""

            # check if table doctype type file is already generated and exists

            if doctype_module_name == table_module_name:

                table_file_path: Path = module_path / \
                    (table_doc.name.replace(" ", "") + ".ts")
                if not table_file_path.exists():
                    if self.generate_child_tables:
                        self._generate_type_definition_file(table_doc, module_path)

                        should_import = True

                else:
                    should_import = True
                
                import_statement = ("import { " + field.options.replace(" ", "") + " } from './" +
                                        field.options.replace(" ", "") + "'") + "\n" if should_import else ''

            else:

                table_module_path: Path = module_path.parent / \
                    table_module_name.replace(" ", "")
                if not table_module_path.exists():
                    table_module_path.mkdir()

                table_file_path: Path = table_module_path / \
                    (table_doc.name.replace(" ", "") + ".ts")

                if not table_file_path.exists():
                    if self.generate_child_tables:
                        self._generate_type_definition_file(table_doc, table_module_path)

                        should_import = True

                else:
                    should_import = True

                import_statement = ("import { " + field.options.replace(" ", "") + " } from '../" +
                                        table_module_name.replace(" ", "") + "/" + field.options.replace(" ", "") + "'") + "\n" if should_import else ''

            return field.options.replace(" ", "") + "[]" if should_import else 'any', import_statement
        return "",None


    def _get_required(self, field):
        if field.reqd:
            return ""
        else:
            return "?"


    def _is_valid_doctype(self, doctype):
        # if (doctype.custom):
        #     print("Custom DocType - ignoring type generation")
        #     return False

        if (doctype.is_virtual):
            print("Virtual DocType - ignoring type generation")
            return False

        return True


# Re-export for backward compatibility (external callers may still import the
# module-level helpers directly).  Down-stream code can instead import the new
# ``TypeGenerator`` class.
__all__ = [
    "TypeGenerator",
    "generate_types_for_doctype",
    "generate_types_for_module",
]


def create_type_definition_file(doc, method=None):
    generator = TypeGenerator(app_name="")
    generator.create_type_definition_file(doc)


def before_migrate():
    # print("Before migrate")
    subprocess.run(
        ["bench", "config", "set-common-config", "-c", "frappe_types_pause_generation", "1"])


def after_migrate():
    # print("After migrate")
    subprocess.run(["bench", "config", "set-common-config",
                   "-c", "frappe_types_pause_generation", "0"])


@frappe.whitelist()
def generate_types_for_doctype(doctype, app_name, generate_child_tables=False, custom_fields=False):
    generator = TypeGenerator(app_name, generate_child_tables=generate_child_tables, custom_fields=custom_fields)
    generator.generate_doctype(doctype)


@frappe.whitelist()
def generate_types_for_module(module, app_name, generate_child_tables=False):
    generator = TypeGenerator(app_name, generate_child_tables=generate_child_tables)
    generator.generate_module(module)