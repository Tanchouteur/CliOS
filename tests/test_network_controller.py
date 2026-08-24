import subprocess
import threading
import time
import unittest

from src.bridge.network_controller import NetworkController, merge_saved_networks, split_terse


class FakeRunner:
    def __init__(self, failures=None):
        self.calls = []
        self.failures = failures or {}

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        key = " ".join(args)
        if key in self.failures:
            failure = self.failures[key]
            if isinstance(failure, BaseException):
                raise failure
            return subprocess.CompletedProcess(args, failure, "", "refusé")
        if "-f WIFI general" in key:
            output = "enabled\n"
        elif "UUID,NAME,TYPE,802-11-wireless.ssid" in key:
            output = "u1:Maison:802-11-wireless:Maison\nu2:Bureau:802-11-wireless:Bureau\ne1:Câble:802-3-ethernet:\n"
        elif "UUID,NAME,TYPE,DEVICE" in key:
            output = "u1:Maison:802-11-wireless:wlan0\n"
        elif "SSID,SIGNAL" in key:
            output = "Maison:82\nInconnu:99\n"
        elif "IP4.ADDRESS" in key:
            output = "IP4.ADDRESS[1]:192.168.1.20/24\n"
        else:
            output = ""
        return subprocess.CompletedProcess(args, 0, output, "")


def wait_idle(controller, timeout=1.0):
    deadline = time.time() + timeout
    while controller.state["busy"] and time.time() < deadline:
        time.sleep(0.005)
    if controller.state["busy"]:
        raise AssertionError("operation did not finish")


class NetworkControllerTest(unittest.TestCase):
    def test_first_publication_can_run_during_owner_initialization(self):
        owner = type("Owner", (), {})()
        owner.closed = False
        publications = []

        def on_change():
            publications.append(owner.closed)

        controller = NetworkController(on_change=on_change, runner=FakeRunner())
        self.assertTrue(controller.refresh())
        wait_idle(controller)
        self.assertGreaterEqual(len(publications), 2)
        self.assertEqual(publications, [False] * len(publications))

    def test_terse_parser_unescapes_colons_and_backslashes(self):
        self.assertEqual(split_terse(r"uuid:Nom\: maison:802-11-wireless:SSID\\5G"),
                         ["uuid", "Nom: maison", "802-11-wireless", r"SSID\5G"])

    def test_scan_only_marks_saved_profiles_as_available(self):
        networks = merge_saved_networks(
            "u1:Maison:802-11-wireless:Maison\nu2:Bureau:802-11-wireless:Bureau",
            "Maison:68\nInconnu:100", "u1:Maison:802-11-wireless:wlan0",
        )
        self.assertEqual([item["uuid"] for item in networks], ["u1", "u2"])
        self.assertTrue(networks[0]["active"])
        self.assertTrue(networks[0]["available"])
        self.assertFalse(networks[1]["available"])

    def test_refresh_publishes_nm_state(self):
        controller = NetworkController(runner=FakeRunner())
        self.assertTrue(controller.refresh())
        wait_idle(controller)
        self.assertTrue(controller.state["available"])
        self.assertEqual(controller.state["active_ssid"], "Maison")
        self.assertEqual(controller.state["ip_address"], "192.168.1.20")

    def test_only_known_uuid_can_connect(self):
        runner = FakeRunner()
        controller = NetworkController(runner=runner)
        controller.refresh(); wait_idle(controller)
        self.assertFalse(controller.connect("inconnu"))
        self.assertTrue(controller.connect("u2")); wait_idle(controller)
        self.assertTrue(any(call[:5] == ["nmcli", "connection", "up", "uuid", "u2"] for call, _ in runner.calls))

    def test_missing_nmcli_timeout_and_command_error_are_reported(self):
        cases = [
            (FileNotFoundError(), "NetworkManager indisponible"),
            (subprocess.TimeoutExpired("nmcli", 1), "Délai NetworkManager dépassé"),
            (subprocess.CompletedProcess([], 10, "", "permission"), "permission"),
        ]
        for result, message in cases:
            def runner(args, **kwargs):
                if isinstance(result, BaseException):
                    raise result
                return result
            controller = NetworkController(runner=runner)
            controller.refresh(); wait_idle(controller)
            self.assertIn(message, controller.state["error"])

    def test_concurrent_operation_is_rejected(self):
        entered = threading.Event()
        release = threading.Event()

        def runner(args, **kwargs):
            entered.set(); release.wait(1)
            return subprocess.CompletedProcess(args, 0, "enabled", "")

        controller = NetworkController(runner=runner)
        self.assertTrue(controller.refresh())
        self.assertTrue(entered.wait(1))
        self.assertFalse(controller.refresh())
        release.set(); wait_idle(controller)


if __name__ == "__main__":
    unittest.main()
