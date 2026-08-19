from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OPS = ROOT / "deploy" / "flarum" / "operations"


class CommunityOperationsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backup = (OPS / "community-backup.sh").read_text(encoding="utf-8")
        cls.restore = (OPS / "community-restore.sh").read_text(encoding="utf-8")
        cls.monitor = (OPS / "community-monitor.sh").read_text(encoding="utf-8")
        cls.offsite = (OPS / "community-offsite-export.sh").read_text(encoding="utf-8")
        cls.install = (OPS / "community-install.sh").read_text(encoding="utf-8")
        cls.zone = (OPS / "nginx-community-security-zone.conf").read_text(encoding="utf-8")
        cls.server = (OPS / "nginx-community-security-server.conf").read_text(encoding="utf-8")

    def test_consistent_encrypted_backup(self) -> None:
        self.assertIn('systemctl stop "$PHP_FPM_SERVICE"', self.backup)
        self.assertIn("--single-transaction", self.backup)
        self.assertIn("--encrypt", self.backup)
        self.assertIn("OpenPGP public-key", self.backup)
        self.assertIn("chmod 0600", self.backup)
        self.assertIn("BACKUP_RETENTION_DAYS", self.backup)
        self.assertIn("flock -w 120", self.backup)

    def test_restore_refuses_production_by_default(self) -> None:
        self.assertIn("TECHFLOW_ALLOW_PRODUCTION_RESTORE", self.restore)
        self.assertIn("DROP DATABASE IF EXISTS", self.restore)
        self.assertIn("community-verify-backup.sh", self.restore)
        self.assertIn("community-verify-backup.sh", self.offsite)
        self.assertIn("chmod 0600", self.offsite)

    def test_monitor_has_required_signals_and_alert_suppression(self) -> None:
        for token in (
            "communityLocal",
            "communityPublic",
            "aiOrchestration",
            "diskUsedPercent",
            "inodeUsedPercent",
            "uploadBytes",
            "backup",
            "criticalLogLines5m",
            "mailDriver",
        ):
            self.assertIn(token, self.monitor)
        self.assertIn("last-alert.fingerprint", self.monitor)
        self.assertIn("backup-in-progress", self.monitor)
        self.assertIn("ALERT_COOLDOWN_SECONDS", self.monitor)
        self.assertIn("TECHFLOW_CHAT_WEBHOOK_URL", self.monitor)
        self.assertIn("mail-driver", self.monitor)
        self.assertNotIn("token=", self.monitor)

    def test_security_policy_and_reversible_install(self) -> None:
        self.assertIn("rate=12r/m", self.zone)
        self.assertIn("server_tokens off", self.zone)
        for header in (
            "X-Frame-Options",
            "Permissions-Policy",
            "Strict-Transport-Security",
        ):
            self.assertIn(header, self.server)
        self.assertIn("X-Content-Type-Options", self.server)
        self.assertIn("Referrer-Policy", self.server)
        self.assertIn("nginx -t", self.install)
        self.assertIn("cp -a", self.install)

    def test_systemd_and_logrotate_assets_exist(self) -> None:
        for name in (
            "techflow-community-backup.service",
            "techflow-community-backup.timer",
            "techflow-community-monitor.service",
            "techflow-community-monitor.timer",
            "techflow-community-ops.logrotate",
        ):
            self.assertTrue((OPS / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
