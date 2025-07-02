import json
from pathlib import Path

import click
import frappe
from frappe.commands import pass_context
from frappe.utils import get_bench_path

from frappe_types.frappe_types.type_generator import (
	TypeGenerationMethod,
	TypeGenerator,
	generate_types_for_doctype,
	generate_types_for_module,
)


@click.command("import-type-gen-settings")
@click.option(
	"--file",
	help="Path to type generation settings file, defaults to frappe_types/seed/seed.json",
	required=False,
)
@pass_context
def import_type_gen_settings(context, file):
	"""Import type generation settings from a JSON file"""
	if not context.sites:
		raise frappe.SiteNotSpecifiedError

	if not file:
		file = f"{get_bench_path()}/apps/frappe_types/frappe_types/seed/seed.json"

	with open(file) as f:
		settings = json.load(f)

	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			doc = frappe.get_single("Type Generation Settings")
			for key, value in settings.items():
				pass
				doc.set(key, value)

			doc.save(ignore_permissions=True)
			frappe.db.commit()
			print(
				f"Saved type generation settings for {site} with settings:\n {json.dumps(settings, indent=4)}"
			)
			frappe.clear_cache(doctype="Type Generation Settings")
		except Exception as e:
			print(f"Error importing type generation settings for {site}: {e}")
		finally:
			frappe.destroy()


@click.command("generate-types-for-doctype")
@click.option("--app", prompt="App Name")
@click.option("--doctype", prompt="Doctype Name")
@click.option(
	"--generate_child_tables",
	default=False,
	is_flag=True,
	prompt="Do you want to generate types for child tables too?",
	help="It will generate Types for child tables includes in the doctype",
)
@click.option(
	"--custom_fields",
	default=False,
	is_flag=True,
	prompt="Do you want to generate types for custom fields too if exists?",
	help="It will generate Types for custom fields includes in the doctype",
)
@pass_context
def generate_types_file_from_doctype(context, app, doctype, generate_child_tables, custom_fields):
	"""Generate types file from doctype"""
	if not app:
		click.echo("Please provide an app with --app")
		return
	print(f"Generating types file for {doctype} in {app}")

	for site in context.sites:
		frappe.connect(site=site)
		try:
			generate_types_for_doctype(doctype, app, generate_child_tables, custom_fields)
		finally:
			frappe.destroy()
	if not context.sites:
		raise frappe.SiteNotSpecifiedError


@click.command("generate-types-for-module")
@click.option("--app", prompt="App Name")
@click.option("--module", prompt="Module Name")
@click.option(
	"--generate_child_tables",
	default=False,
	is_flag=True,
	prompt="Do you want to generate types for child tables too?",
	help="It will generate Types for child tables includes in the doctype",
)
@pass_context
def generate_types_file_from_module(context, app, module, generate_child_tables):
	"""Generate types file from module"""
	if not app:
		click.echo("Please provide an app with --app")
		return
	print(f"Generating types file for {module} in {app}")

	for site in context.sites:
		frappe.connect(site=site)
		try:
			generate_types_for_module(module, app, generate_child_tables)
		finally:
			frappe.destroy()
	if not context.sites:
		raise frappe.SiteNotSpecifiedError


@click.command(
	"generate-types",
	help="Generate types for all apps of the current site. Use import-type-gen-settings to configure.",
)
@pass_context
def generate_types(context):
	"""Generate types for all apps of the current site"""
	if not context.sites:
		raise frappe.SiteNotSpecifiedError

	for site in context.sites:
		frappe.connect(site=site)

		try:
			generator = TypeGenerator(app_name="")
			generator.export_all_apps()
		except Exception as e:
			print(f"Error exporting types for {site}: {e}")
		finally:
			frappe.destroy()


commands = [
	generate_types_file_from_doctype,
	generate_types_file_from_module,
	generate_types,
	import_type_gen_settings,
]
