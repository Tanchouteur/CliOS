import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UsbAutomountContractTest(unittest.TestCase):
    def _read(self, relative_path: str) -> str:
        with open(os.path.join(ROOT, relative_path), encoding="utf-8") as stream:
            return stream.read()

    def test_udev_only_requests_mount_for_usb_filesystems(self):
        rule = self._read("installation/etc/udev/rules.d/90-clios-usb-storage.rules")
        self.assertIn('SUBSYSTEM=="block"', rule)
        self.assertIn('ENV{ID_FS_USAGE}=="filesystem"', rule)
        self.assertIn('clios-usb-mount@%k.service', rule)
        self.assertTrue('ENV{ID_BUS}=="usb"' in rule or 'ENV{ID_PATH}=="*usb*"' in rule)

    def test_systemd_unit_is_bound_to_device_and_uses_closed_helper(self):
        unit = self._read("installation/etc/systemd/system/clios-usb-mount@.service")
        self.assertIn("BindsTo=dev-%i.device", unit)
        self.assertIn("ExecStart=/usr/local/libexec/clios-usb-mount mount %I", unit)
        self.assertIn("ExecStop=/usr/local/libexec/clios-usb-mount unmount %I", unit)
        self.assertNotIn("/bin/sh", unit)
        self.assertNotIn("/bin/bash", unit)

    def test_helper_restricts_device_name_and_mount_options(self):
        helper = self._read("installation/usr/local/libexec/clios-usb-mount")
        self.assertIn('BLOCK_NAME" =~ ^[a-zA-Z0-9._-]+$', helper)
        self.assertIn("device_is_usb", helper)
        self.assertIn("nosuid,nodev,noexec", helper)
        self.assertIn('MOUNT_POINT="${MEDIA_ROOT}/${BLOCK_NAME}"', helper)

    def test_installer_installs_and_uninstalls_automount_components(self):
        installer = self._read("install.sh")
        for component in (
            "clios-usb-mount@.service",
            "90-clios-usb-storage.rules",
            "clios-usb-mount",
            "exfatprogs",
            "ntfs-3g",
        ):
            self.assertIn(component, installer)


if __name__ == "__main__":
    unittest.main()
