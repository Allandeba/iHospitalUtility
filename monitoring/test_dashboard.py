"""Dashboard acceptance contracts (no real telemetry fabricated)."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent

class DashboardTests(unittest.TestCase):
    def test_unknown_certificate_expiry_is_not_a_negative_validity(self):
        board = json.loads((ROOT / 'dashboard.json').read_text())
        certificate = next(p for p in board['panels'] if p['id'] == 4)
        self.assertIn('> 0', certificate['targets'][0]['expr'])

    def test_queries_distinguish_stale_missing_and_failure(self):
        path = ROOT / 'dashboard.json'
        self.assertTrue(path.exists(), 'Dashboard must exist')
        board = json.loads(path.read_text())
        self.assertEqual(board['uid'], 'ihospitalutility-overview')
        self.assertEqual(board['title'], 'iHospitalUtility · Visão geral')
        targets = [t for p in board['panels'] for t in p.get('targets', [])]
        metrics = [t['expr'] for t in targets if 'expr' in t]
        self.assertGreaterEqual(len(metrics), 7)
        self.assertFalse(any('vector(0)' in q for q in metrics))
        self.assertTrue(any('time() -' in q and 'last_run' in q for q in metrics))
        self.assertTrue(all('ihospitalutility-monitor' in q for q in metrics))
        self.assertTrue(any('loki' == p.get('datasource', {}).get('uid') for p in board['panels']))
        content = ' '.join(p.get('options', {}).get('content', '') for p in board['panels'])
        self.assertIn('offline', content)
        self.assertIn('clínicos', content)
        self.assertIn('7 dias', content)
        self.assertIn('72 horas', content)
        for p in board['panels']:
            if p['type'] == 'stat':
                self.assertEqual(p['fieldConfig']['defaults']['noValue'], 'Sem telemetria')

if __name__ == '__main__':
    unittest.main()
