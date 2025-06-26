import os
import subprocess
from enum import Enum
from pathlib import Path

import frappe
from frappe.core.doctype.docfield.docfield import DocField
from frappe.core.doctype.doctype.doctype import DocType

from .utils import create_file, get_bench_root_path, is_developer_mode_enabled, to_ts_type
from .whitelist_methods_generator import generate_interface as generate_whitelist_interface


class TypeGenerationMethod(Enum):
	DOCTYPES = "doctypes"
	MODULES = "modules"
	ALL_APPS = "all_apps"


class TypeGenerator:
	"""Generator for TypeScript type definitions for DocTypes

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
	    standard ones
	"""

	def __init__(
		self,
		app_name: str,
		*,
		generate_child_tables: bool = False,
		custom_fields: bool = False,
	) -> None:
		self.app_name = app_name
		self.generate_child_tables = generate_child_tables
		self.custom_fields = custom_fields
		self.doctype_map = []
		self.type_generation_method = None

		settings = self._get_type_generation_settings()
		base_output_path = settings.get("base_output_path")
		if base_output_path:
			self.base_output_path = base_output_path

		should_export_to_root = settings.get("export_to_root")
		if not should_export_to_root and not base_output_path:
			print("Setting base output path to '../apps'")
			self.base_output_path = "../apps"

		if not hasattr(self, "base_output_path"):
			self.base_output_path = ""

	# ---------------------------------------------------------------------
	# Public API
	# ---------------------------------------------------------------------
	def generate_doctype(self, doctype: str):
		"""Generate a `.d.ts` type definition file for a single DocType."""
		if not self.type_generation_method:
			self.type_generation_method = TypeGenerationMethod.DOCTYPES

		try:
			# custom_fields True means that the generate .d.ts file for custom fields with original fields
			doc = frappe.get_meta(doctype) if self.custom_fields else frappe.get_doc("DocType", doctype)

			if not self._can_generate(doc):
				return

			print("Generating type definition file for " + doc.name)
			module_name = doc.module

			module_path = self._get_module_path(self.app_name, module_name)
			if module_path:
				self._generate_type_definition_file(doc, module_path)
				# Accumulate this DocType for the map
				ts_name = to_ts_type(doc.name)
				module_dir = to_ts_type(module_name)
				self.doctype_map.append((doc.name, ts_name, module_dir))
				if self.type_generation_method == TypeGenerationMethod.DOCTYPES:
					self._write_doctype_map()

		except Exception as e:
			err_msg = f": {e!s}\n{frappe.get_traceback()}"
			print(f"An error occurred while generating type for {doctype} {err_msg}")

	def generate_module(self, module: str):
		"""Generate type definition files for *all* DocTypes inside *module*."""
		if not self.type_generation_method:
			self.type_generation_method = TypeGenerationMethod.MODULES
		try:
			child_tables = [
				doctype["name"]
				for doctype in frappe.get_list("DocType", filters={"module": module, "istable": 1})
			]
			if len(child_tables) > 0:
				for child_table in child_tables:
					self.generate_doctype(child_table)

			doctypes = [
				doctype["name"]
				for doctype in frappe.get_list("DocType", filters={"module": module, "istable": 0})
			]

			if len(doctypes) > 0:
				for doctype in doctypes:
					self.generate_doctype(doctype)

				if self.type_generation_method == TypeGenerationMethod.MODULES:
					self._write_doctype_map()
		except Exception as e:
			err_msg = f": {e!s}\n{frappe.get_traceback()}"
			print(f"An error occurred while generating type for {module} {err_msg}")

	def update_type_definition_file(self, doctype: DocType):
		"""Update a `.d.ts` type definition file for a single DocType.
		Called when a DocType is updated.
		"""
		if self._is_migrating_or_installing():
			print("Skipping type generation in patch, migrate, install or setup wizard")
			return

		if not self._can_generate(doctype):
			return

		# Ignore core apps
		if self.app_name in {"frappe", "erpnext"}:
			print("Ignoring core app DocTypes")
			return

		print("Generating type definition file for " + doctype.name)
		module_name = doctype.module
		app_name = frappe.db.get_value("Module Def", module_name, "app_name")

		module_path = self._get_module_path(app_name, module_name)
		if module_path:
			self._generate_type_definition_file(doctype, module_path)

	def export_all_apps(self):
		"""Generate type definitions for all configured apps."""
		settings = self._get_type_generation_settings()
		type_settings = settings.get("type_settings", [])
		export_to_root = settings.get("export_to_root")
		for ts in type_settings:
			app_name = ts["app_name"]
			print(f"Generating type definitions for app {app_name}")
			generator = type(self)(
				app_name,
				generate_child_tables=self.generate_child_tables,
				custom_fields=self.custom_fields,
			)
			generator.type_generation_method = TypeGenerationMethod.ALL_APPS
			modules = [m["name"] for m in frappe.get_list("Module Def", filters={"app_name": app_name})]
			for module in modules:
				generator.generate_module(module)

			if export_to_root:
				# accumulate doctypes for root map
				self.doctype_map.extend(generator.doctype_map)
			else:
				# write per-app map
				generator._write_doctype_map()
		if export_to_root:
			# write combined root map
			self._write_doctype_map()

		# Export whitelist methods interface
		print("Generating whitelist methods interface")
		bench_root = Path(get_bench_root_path())
		search_root = bench_root / "apps"
		# Determine output directory for whitelist interface
		if export_to_root:
			root_path = settings.get("root_output_path", "types")
			out_dir = Path(self.base_output_path) / root_path
			if not out_dir.is_absolute():
				out_dir = Path(get_bench_root_path()) / root_path
		else:
			# Write whitelist interface to bench root types directory
			out_dir = Path(get_bench_root_path()) / "types"
		out_dir.mkdir(parents=True, exist_ok=True)
		out_file = out_dir / "FrappeWhitelistedMethods.d.ts"
		generate_whitelist_interface(search_root, out_file)

	# ---------------------------------------------------------------------
	# Private methods
	# ---------------------------------------------------------------------
	def _can_generate(self, doctype: DocType) -> bool:
		if self._is_generation_paused():
			print("Frappe Types is paused")
			return False

		if not is_developer_mode_enabled():
			print("Developer mode is not enabled")
			return False

		if not self._is_valid_doctype(doctype):
			return False

		return True

	def _is_migrating_or_installing(self) -> bool:
		return (
			frappe.flags.in_patch
			or frappe.flags.in_migrate
			or frappe.flags.in_install
			or frappe.flags.in_setup_wizard
		)

	def _is_generation_paused(self) -> bool:
		"""Return True if type generation has been temporarily disabled via
		the `frappe_types_pause_generation` flag in *common_site_config*."""
		is_paused_config = frappe.get_conf().get("frappe_types_pause_generation", 0)
		return bool(is_paused_config)

	def _get_module_path(self, app_name: str, module_name: str) -> Path | None:
		"""Return the directory for type output. If export_to_root is set, always use the root types dir."""
		settings = self._get_type_generation_settings()
		if settings.get("export_to_root"):
			# Determine root output path
			root_path = settings.get("root_output_path", "types")
			path_obj = Path(os.path.join(self.base_output_path, root_path, self.app_name))

			# If relative, assume bench root
			if not path_obj.is_absolute():
				bench_root = get_bench_root_path()
				path_obj = Path(os.path.join(bench_root, root_path))

			path_obj.mkdir(parents=True, exist_ok=True)
			module_path = path_obj / to_ts_type(module_name)
			module_path.mkdir(exist_ok=True)

			return module_path

		app_path = Path(self.base_output_path) / app_name
		if not app_path.exists():
			print("App path does not exist - ignoring type generation")
			return None

		# Look-up path in Type Generation Settings
		type_generation_settings = self._get_type_generation_settings()["type_settings"]
		type_setting = next((ts for ts in type_generation_settings if ts["app_name"] == app_name), None)
		if not type_setting:
			return None

		# Ensure directories exist
		type_path: Path = app_path / type_setting["app_path"] / "types"
		type_path.mkdir(parents=True, exist_ok=True)

		module_path: Path = type_path / to_ts_type(module_name)
		module_path.mkdir(exist_ok=True)
		return module_path

	def _get_type_generation_settings(self) -> dict:
		return frappe.get_doc("Type Generation Settings").as_dict()

	def _generate_type_definition_file(self, doctype: DocType, module_path: Path):
		doctype_name = to_ts_type(doctype.name)
		type_file_path = module_path / (doctype_name + ".d.ts")
		type_file_content = self._generate_type_definition_content(doctype, module_path)

		create_file(type_file_path, type_file_content)

	def _generate_type_definition_content(self, doctype: DocType, module_path: Path):
		"""Return the TypeScript interface for a DocType.

		The generated string contains:
		1. Optional import statements (for child tables etc.)
		2. The `export interface` block with core document fields and
		   any custom fields from the DocType definition.
		"""
		# Collect import lines without duplicates while preserving order
		import_lines: list[str] = []

		interface_name = to_ts_type(doctype.name)
		# DocType is a global interface defined in @frappe/types
		lines: list[str] = [f"export interface {interface_name} extends DocType {{"]

		# --- We override the name field to be consistent with the naming rule
		name_type = "number" if doctype.naming_rule == "Autoincrement" else "string"
		core_fields = [
			f"\tname: {name_type}",
		]
		lines.extend(core_fields)

		# --- Custom fields
		ignored_field_types = {
			"Section Break",
			"Column Break",
			"HTML",
			"Button",
			"Fold",
			"Heading",
			"Tab Break",
			"Break",
		}

		for field in doctype.fields:
			if field.fieldtype in ignored_field_types:
				continue

			# Add comment line
			lines.append(self._get_field_comment(field).rstrip())

			# Add field definition and track needed imports
			field_def, import_stmt = self._get_field_type_definition(field, doctype, module_path)
			if import_stmt and import_stmt not in import_lines:
				import_lines.append(import_stmt)
			lines.append(f"\t{field_def}")

		lines.append("}")

		import_block = "".join(import_lines)  # each statement already ends with \n
		interface_block = "\n".join(lines)

		# Ensure a blank line between imports and interface (even if no imports)
		return f"{import_block}\n{interface_block}"

	def _get_field_comment(self, field: DocField) -> str:
		"""Return a single-line JSDoc comment for the given field.

		Format: \t/**\t<label> : <FieldType> [ - extra]\t*/\n
		"""
		# Extra information shown after the field type
		desc: str = field.description or ""

		# For link / table fields we include the linked DocType before description
		if field.fieldtype in {"Link", "Table", "Table MultiSelect"}:
			linked = field.options or ""
			extra = f" - {field.description}" if field.description else ""
			desc = f"{linked}{extra}"

		label = field.label or ""
		comment = f"{label} : {field.fieldtype}"
		if desc:
			comment += f" - {desc}"

		# Surround comment with tabs to keep alignment
		return f"\t/**\t{comment}\t*/\n"

	def _get_field_type_definition(self, field: DocField, doctype: DocType, module_path: Path):
		field_type, import_statement = self._get_field_type(field, doctype, module_path)
		return (
			field.fieldname + self._get_required(field) + ": " + field_type,
			import_statement,
		)

	def _get_field_type(self, field: DocField, doctype: DocType, module_path: Path):
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
			if field.options:
				options = field.options.split("\n")
				t = ""
				for option in options:
					t += '"' + option + '" | '
				if t.endswith(" | "):
					t = t[:-3]
				return t, None
			else:
				return "string", None

		if field.fieldtype in basic_fieldtypes:
			return basic_fieldtypes[field.fieldtype], None
		else:
			return "any", None

	def _get_imports_for_table_fields(
		self, field: DocField, doctype: DocType, module_path: Path
	) -> tuple[str, str | None]:
		"""Resolve TypeScript type & import statement for Table fields.

		Returns a tuple `(ts_type, import_stmt)` where `import_stmt` is an empty
		string when no import is needed. For non-table fields the function
		returns ("", None).
		"""
		if field.fieldtype not in {"Table", "Table MultiSelect"}:
			return "", None  # Not a child-table field

		# -- Identify child table DocType & locations
		table_doc = frappe.get_doc("DocType", field.options)
		same_module = table_doc.module == doctype.module

		ts_module_name = to_ts_type(table_doc.module)
		ts_doc_name = to_ts_type(table_doc.name)

		# Determine destination folder for the child type file and relative import path
		if same_module:
			target_dir = module_path
			import_path = f"./{ts_doc_name}"
		else:
			target_dir = module_path.parent / ts_module_name
			target_dir.mkdir(exist_ok=True)
			import_path = f"../{ts_module_name}/{ts_doc_name}"

		ts_file_path = target_dir / f"{ts_doc_name}.d.ts"

		# -- Decide whether we can / should import
		if not ts_file_path.exists():
			if self.generate_child_tables:
				# Generate the missing child type definition
				self._generate_type_definition_file(table_doc, target_dir)
			else:
				# No file & not allowed to generate → treat as `any`
				return "any", ""

		# At this point the file exists (either previously or just generated)
		import_stmt = f"import {{ {ts_doc_name} }} from '{import_path}'\n"
		return f"{ts_doc_name}[]", import_stmt

	def _get_required(self, field):
		if field.reqd:
			return ""
		else:
			return "?"

	def _is_valid_doctype(self, doctype: DocType) -> bool:
		type_generation_settings = self._get_type_generation_settings()
		if not type_generation_settings.get("include_custom_doctypes", False) and (doctype.custom):
			print("Custom DocType - ignoring type generation")
			return False

		if doctype.is_virtual:
			print("Virtual DocType - ignoring type generation")
			return False

		return True

	def _write_doctype_map(self):
		"""Generate a TypeScript type mapping DocType names to TS interfaces."""
		settings = self._get_type_generation_settings()
		export_to_root = settings.get("export_to_root")
		if export_to_root:
			root_path = settings.get("root_output_path", "types")
			base_path = Path(os.path.join(self.base_output_path, root_path))
			if not base_path.is_absolute():
				bench_root = get_bench_root_path()
				base_path = Path(os.path.join(bench_root, root_path))
			output_base = base_path
		else:
			app_path = Path(self.base_output_path) / self.app_name
			type_settings = settings.get("type_settings", [])
			type_setting = next((ts for ts in type_settings if ts["app_name"] == self.app_name), None)
			if not type_setting:
				print(f"No type setting found for app {self.app_name} - skipping DocTypeMap")
				return
			output_base = app_path / type_setting["app_path"] / "types"

		# Collect doctypes generated so far
		dt_map = self.doctype_map
		# Ensure unique entries
		dt_map = list(set(dt_map))

		# Build import statements
		seen = set()
		imports = []
		for _, ts_name, module_dir in dt_map:
			if ts_name not in seen:
				imports.append(f"import {{ {ts_name} }} from './{module_dir}/{ts_name}';\n")
				seen.add(ts_name)

		# Build DocTypeMap type
		lines = ["declare global {\n  interface DocTypeMap {"]
		for orig, ts_name, _ in dt_map:
			lines.append(f'    "{orig}": {ts_name};')
		lines.append("  }\n}\n")
		lines.append("export {};")
		content = "".join(imports) + "\n" + "\n".join(lines)

		# Write file
		map_file = output_base / "DocTypeMap.d.ts"
		create_file(map_file, content)
		self.doctype_map = []


# Should probably be renamed to `update_type_definition_file`
def create_type_definition_file(doc, method=None):
	# Flag meant only to be used in testing and development
	if frappe.flags.type_generator_disable_update:
		return

	# App name is not needed for updating the definition file
	generator = TypeGenerator(app_name="")
	generator.update_type_definition_file(doc)


def before_migrate():
	# print("Before migrate")
	subprocess.run(
		[
			"bench",
			"config",
			"set-common-config",
			"-c",
			"frappe_types_pause_generation",
			"1",
		]
	)


def after_migrate():
	# print("After migrate")
	subprocess.run(
		[
			"bench",
			"config",
			"set-common-config",
			"-c",
			"frappe_types_pause_generation",
			"0",
		]
	)


@frappe.whitelist()
def generate_types_for_doctype(
	doctype: str, app_name: str, generate_child_tables: bool = False, custom_fields: bool = False
):
	generator = TypeGenerator(
		app_name,
		generate_child_tables=generate_child_tables,
		custom_fields=custom_fields,
	)
	generator.generate_doctype(doctype)


@frappe.whitelist()
def generate_types_for_module(module: str, app_name: str, generate_child_tables: bool = False):
	generator = TypeGenerator(app_name, generate_child_tables=generate_child_tables)
	generator.generate_module(module)


@frappe.whitelist()
def export_all_apps():
	type_settings = frappe.get_single("Type Generation Settings")
	type_settings.base_output_path = ""
	type_settings.save()
	generator = TypeGenerator(app_name="")
	generator.export_all_apps()

	return "Success"
