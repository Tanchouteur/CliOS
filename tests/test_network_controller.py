import subprocess
import threading
import time
import unittest

from src.bridge.network_controller import (
    NetworkController,
    merge_saved_networks,
    parse_visible_networks,
    split_terse,
)


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
        elif "UUID,NAME,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY" in key:
            output = (
                "u1:Maison:802-11-wireless:yes:100\nu2:Bureau:802-11-wireless:no:0\ne1:Câble:802-3-ethernet:yes:0\n"
            )
        elif "802-11-wireless.ssid" in key and key.endswith("uuid u1"):
            output = "Maison\n"
        elif "802-11-wireless.ssid" in key and key.endswith("uuid u2"):
            output = "Bureau\n"
        elif "UUID,TYPE,DEVICE" in key:
            output = "u1:802-11-wireless:wlan0\n"
        elif "SSID,SIGNAL,SECURITY" in key:
            output = "Maison:82:WPA2\nInconnu:99:WPA2\nCafe:45:--\n"
        elif "IP4.ADDRESS device show wlan0" in key:
            output = "192.168.1.20/24\n"
        elif "-f CONNECTIVITY general" in key:
            output = "full\n"
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
        controller = NetworkController(on_change=lambda: publications.append(owner.closed), runner=FakeRunner())
        self.assertTrue(controller.refresh())
        wait_idle(controller)
        self.assertGreaterEqual(len(publications), 2)
        self.assertEqual(publications, [False] * len(publications))

    def test_terse_parser_unescapes_colons_and_backslashes(self):
        self.assertEqual(
            split_terse(r"uuid:Nom\: maison:802-11-wireless:SSID\\5G"),
            ["uuid", "Nom: maison", "802-11-wireless", r"SSID\5G"],
        )

    def test_scan_marks_profiles_and_exposes_unknown_access_points(self):
        networks = merge_saved_networks(
            "u1:Maison:802-11-wireless:Maison:yes:100\nu2:Bureau:802-11-wireless:Bureau:no:0",
            "Maison:68:WPA2\nInconnu:100:WPA2",
            "u1:802-11-wireless:wlan0",
        )
        visible = parse_visible_networks("Maison:68:WPA2\nInconnu:100:WPA2", networks)
        self.assertEqual([item["uuid"] for item in networks], ["u1", "u2"])
        self.assertTrue(networks[0]["active"])
        self.assertTrue(networks[0]["autoconnect"])
        self.assertEqual(networks[0]["priority"], 100)
        self.assertFalse(networks[1]["available"])
        self.assertEqual(visible[1]["ssid"], "Inconnu")
        self.assertFalse(visible[1]["saved"])

    def test_refresh_uses_supported_fields_and_active_wifi_device(self):
        runner = FakeRunner()
        controller = NetworkController(runner=runner)
        self.assertTrue(controller.refresh())
        wait_idle(controller)
        self.assertTrue(controller.state["available"])
        self.assertEqual(controller.state["active_ssid"], "Maison")
        self.assertEqual(controller.state["active_device"], "wlan0")
        self.assertEqual(controller.state["ip_address"], "192.168.1.20")
        self.assertEqual(controller.state["connectivity"], "full")
        commands = [" ".join(call) for call, _ in runner.calls]
        self.assertFalse(any("UUID,NAME,TYPE,802-11-wireless.ssid" in call for call in commands))
        self.assertTrue(all(kwargs["env"]["LC_ALL"] == "C" for _, kwargs in runner.calls))

    def test_scan_failure_preserves_saved_profiles_and_reports_warning(self):
        scan = "nmcli -t --escape yes -f SSID,SIGNAL,SECURITY device wifi list --rescan yes"
        controller = NetworkController(runner=FakeRunner({scan: 10}))
        controller.refresh()
        wait_idle(controller)
        self.assertTrue(controller.state["available"])
        self.assertEqual(len(controller.state["saved_networks"]), 2)
        self.assertIn("refusé", controller.state["error"])

    def test_connect_add_forget_and_preferences_are_bounded_to_known_state(self):
        runner = FakeRunner()
        controller = NetworkController(runner=runner)
        controller.refresh()
        wait_idle(controller)
        self.assertFalse(controller.connect("inconnu"))
        self.assertTrue(controller.connect("u2"))
        wait_idle(controller)
        self.assertTrue(controller.add_network("Inconnu", "secret123"))
        wait_idle(controller)
        self.assertTrue(controller.forget("u2"))
        wait_idle(controller)
        self.assertTrue(controller.set_autoconnect("u2", True))
        wait_idle(controller)
        self.assertTrue(controller.set_preferred("u2"))
        wait_idle(controller)
        commands = [call for call, _ in runner.calls]
        self.assertIn(["nmcli", "connection", "up", "uuid", "u2"], commands)
        self.assertIn(["nmcli", "--ask", "device", "wifi", "connect", "Inconnu"], commands)
        secret_call = next(
            kwargs for call, kwargs in runner.calls
            if call == ["nmcli", "--ask", "device", "wifi", "connect", "Inconnu"]
        )
        self.assertEqual(secret_call["input"], "secret123\n")
        self.assertFalse(any("secret123" in argument for call in commands for argument in call))
        self.assertIn(["nmcli", "connection", "delete", "uuid", "u2"], commands)
        self.assertIn(
            ["nmcli", "connection", "modify", "uuid", "u2", "connection.autoconnect", "yes"],
            commands,
        )
        self.assertIn(
            ["nmcli", "connection", "modify", "uuid", "u2", "connection.autoconnect-priority", "100"],
            commands,
        )

    def test_open_network_does_not_require_password(self):
        runner = FakeRunner()
        controller = NetworkController(runner=runner)
        controller.refresh()
        wait_idle(controller)
        self.assertTrue(controller.add_network("Cafe"))
        wait_idle(controller)
        self.assertIn(["nmcli", "device", "wifi", "connect", "Cafe"], [c for c, _ in runner.calls])

    def test_missing_nmcli_timeout_and_command_error_are_reported(self):
        cases = [
            (FileNotFoundError(), "NetworkManager indisponible", False),
            (subprocess.TimeoutExpired("nmcli", 1), "Délai NetworkManager dépassé", True),
            (subprocess.CompletedProcess([], 10, "", "permission denied"), "Autorisation réseau refusée", True),
        ]
        for result, message, available in cases:

            def runner(args, **kwargs):
                if isinstance(result, BaseException):
                    raise result
                return result

            controller = NetworkController(runner=runner)
            controller.refresh()
            wait_idle(controller)
            self.assertIn(message, controller.state["error"])
            self.assertEqual(controller.state["available"], available)

    def test_concurrent_operation_is_rejected(self):
        entered, release = threading.Event(), threading.Event()

        def runner(args, **kwargs):
            entered.set()
            release.wait(1)
            return subprocess.CompletedProcess(args, 0, "enabled", "")

        controller = NetworkController(runner=runner)
        self.assertTrue(controller.refresh())
        self.assertTrue(entered.wait(1))
        self.assertFalse(controller.refresh())
        release.set()
        wait_idle(controller)


if __name__ == "__main__":
    unittest.main()
