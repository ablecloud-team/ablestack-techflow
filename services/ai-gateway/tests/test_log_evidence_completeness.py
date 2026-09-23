import unittest

from app.log_artifacts import parse_log_artifact


class LogEvidenceCompletenessTests(unittest.TestCase):
    def test_small_diagnostic_keeps_topology_between_errors_and_masks_secrets(self):
        data = ('normal\n' * 30 + '/mnt/glue-gfs /dev/mapper/vg_glue-lv_glue gfs2\n'
                'sdm -> mpatha -> vg_glue-lv_glue\npassword=do-not-retain\n'
                + 'normal\n' * 30 + 'I/O error dev sdm\n').encode()
        result = parse_log_artifact('diagnostic.txt', 'text/plain', data,
                                    max_entries=100, max_extracted_bytes=100000,
                                    max_ratio=20, max_evidence_chars=120000)
        self.assertIn('sdm -> mpatha -> vg_glue-lv_glue', result.evidence_text)
        self.assertIn('/mnt/glue-gfs', result.evidence_text)
        self.assertNotIn('do-not-retain', result.evidence_text)
        self.assertFalse(result.truncated)


if __name__ == '__main__':
    unittest.main()
