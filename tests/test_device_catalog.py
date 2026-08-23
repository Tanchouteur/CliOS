import unittest

from src.ble.device_catalog import BleDevice, DeviceCatalog, MAX_DEVICES


class MemoryStorage:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


def device(index=0, **changes):
    values = dict(
        id=f"dev_{index}", name=f"LED {index}", ble_address=f"AA:{index:02X}",
        protocol="LOTUS_9B", gatt_char_uuid="fff3", write_with_response=False,
        advertised_name="ELK-BLEDOM",
    )
    values.update(changes)
    return BleDevice(**values)


class DeviceCatalogTest(unittest.TestCase):
    def test_crud_is_persisted(self):
        storage = MemoryStorage()
        catalog = DeviceCatalog(storage)
        catalog.add_device(device())
        self.assertTrue(catalog.update_device("dev_0", name="Plancher", brightness=42))
        restored = DeviceCatalog(storage).get_device("dev_0")
        self.assertEqual(restored.name, "Plancher")
        self.assertEqual(restored.brightness, 42)
        self.assertTrue(catalog.remove_device("dev_0"))

    def test_limit_and_duplicate_addresses_are_rejected(self):
        catalog = DeviceCatalog(None)
        catalog.add_device(device())
        with self.assertRaisesRegex(ValueError, "deja configure"):
            catalog.add_device(device(9, ble_address="aa:00"))
        for index in range(1, MAX_DEVICES):
            catalog.add_device(device(index))
        with self.assertRaisesRegex(ValueError, "Limite"):
            catalog.add_device(device(MAX_DEVICES))

    def test_legacy_values_are_migrated_without_deletion(self):
        prefix = "services.Leds.params."
        storage = MemoryStorage({
            prefix + "dash_mac": "AA:BB", prefix + "dash_proto": "LEDCAR_DMX_9B",
            prefix + "foot_mac": "CC:DD", prefix + "foot_proto": "LOTUS_9B",
        })
        catalog = DeviceCatalog(storage)
        self.assertEqual({item.name for item in catalog.list_devices()}, {"Habitacle", "Plancher"})
        self.assertEqual(storage.get(prefix + "dash_mac"), "AA:BB")

    def test_group_controls_effective_color_brightness_and_power(self):
        catalog = DeviceCatalog(None)
        catalog.add_device(device(brightness=80))
        group_id = catalog.add_group("Portieres")
        catalog.add_device_to_group("dev_0", group_id)
        catalog.update_group(group_id, color_override="#123456", brightness=50, enabled=False)
        current = catalog.get_device("dev_0")
        self.assertEqual(catalog.get_effective_color(current, "#FFFFFF"), "#123456")
        self.assertEqual(catalog.get_effective_brightness(current), 40)
        self.assertFalse(catalog.is_effectively_enabled(current))


if __name__ == "__main__":
    unittest.main()
