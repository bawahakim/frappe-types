# Copyright (c) 2025, Hakim Bawa and Contributors
# See license.txt

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from frappe_types.frappe_types.type_generator import generate_types_indexes

class TestTypeGenerator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for types
        self.tmp_dir = tempfile.mkdtemp()
        self.types_dir = Path(self.tmp_dir) / "types"
        self.types_dir.mkdir()
        self.module1 = self.types_dir / "ModuleA"
        self.module2 = self.types_dir / "ModuleB"
        self.module1.mkdir()
        self.module2.mkdir()
        (self.module1 / "Doc1.ts").write_text("export interface Doc1 {}\n")
        (self.module1 / "Doc2.ts").write_text("export interface Doc2 {}\n")
        (self.module2 / "Doc3.ts").write_text("export interface Doc3 {}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_generate_types_indexes(self):
        generate_types_indexes(self.types_dir)
        # Module index
        module1_index = (self.module1 / "index.ts").read_text()
        module2_index = (self.module2 / "index.ts").read_text()
        self.assertIn('export * from "./Doc1";', module1_index)
        self.assertIn('export * from "./Doc2";', module1_index)
        self.assertIn('export * from "./Doc3";', module2_index)
        # Root index
        root_index = (self.types_dir / "index.ts").read_text()
        self.assertIn('export * as ModuleA from "./ModuleA/index";', root_index)
        self.assertIn('export * as ModuleB from "./ModuleB/index";', root_index)

if __name__ == "__main__":
    unittest.main()