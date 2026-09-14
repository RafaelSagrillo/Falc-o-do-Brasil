import unittest,tempfile,shutil
from pathlib import Path
from parse_job import classify,parse

class RoutingTests(unittest.TestCase):
    def test_family_cannot_enter_company(self):
        with self.assertRaisesRegex(ValueError,'scope_mismatch'):
            classify('Relação de Títulos a Pagar DESPESA FIXA REMY','empresa')
    def test_company_cannot_enter_family(self):
        with self.assertRaisesRegex(ValueError,'scope_mismatch'):
            classify('Relação de Títulos a Pagar DESPESA FIXA FALCAO','familia')
    def test_unknown_is_not_guessed(self):
        with self.assertRaises(ValueError): classify('Meu relatorio novo','empresa')
    def test_renamed_real_pdf(self):
        source=Path(__file__).resolve().parent.parent/'upload/Despesa Remy 2026.pdf'
        if not source.exists():self.skipTest('Fixture privada nao acompanha o pacote')
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'source.pdf';shutil.copyfile(source,dest)
            r=parse(dest,'familia','arquivo-renomeado.pdf')
            self.assertEqual(r['document']['original_name'],'arquivo-renomeado.pdf')
            self.assertEqual(r['document']['scope'],'familia')
            self.assertEqual(len(r['rows']),277)
            self.assertEqual(r['validation']['calculated']['principal'],'824775.72')
            self.assertEqual(r['document']['status'],'validated')

if __name__=='__main__':unittest.main()
