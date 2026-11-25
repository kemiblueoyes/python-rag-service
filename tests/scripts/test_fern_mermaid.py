import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "doc-infrastructure/scripts/fern_mermaid.py"
spec = importlib.util.spec_from_file_location("fern_mermaid", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

THEME = mod.load_classes(ROOT / "doc-infrastructure/diagram-styles/mermaid-theme.json")


class MermaidTest(unittest.TestCase):
    def test_replaces_old_classes_and_keeps_assignments(self):
        source = (
            "Some prose\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            " A[Foo] --> B[Bar]\n"
            " classDef core fill:#ABCDEF,stroke:#000000,color:#000000\n"
            " class A core\n"
            "```\n"
        )
        result = mod.inject_mermaid(source, THEME)
        self.assertIn("class A core", result)
        self.assertNotIn("#ABCDEF", result)
        self.assertEqual(result.count("classDef core"), 1)
        self.assertEqual(mod.inject_mermaid(result, THEME), result)

    def test_does_not_modify_sequence_or_non_mermaid(self):
        source = (
            "```mermaid\n"
            "sequenceDiagram\n"
            " A->>B: hello\n"
            "```\n"
            "```bash\n"
            "echo hi\n"
            "```\n"
        )
        self.assertEqual(mod.inject_mermaid(source, THEME), source)

    def test_can_stage_and_remove_deleted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'fern'
            dst = root / '.generated' / 'fern'
            src.mkdir()
            (src / 'docs.yml').write_text('title: Test\n')
            (src / 'page.mdx').write_text('```mermaid\nflowchart TD\n A --> B\n```\n')
            mod.stage(src, dst, THEME)
            self.assertIn('classDef core', (dst / 'page.mdx').read_text())
            (src / 'page.mdx').unlink()
            mod.stage(src, dst, THEME)
            self.assertFalse((dst / 'page.mdx').exists())


if __name__ == '__main__':
    unittest.main()
