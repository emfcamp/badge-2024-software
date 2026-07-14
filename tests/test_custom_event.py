import unittest

from events.custom import CustomEvent


class CustomEventTest(unittest.TestCase):
    def test_getitem_reads_from_data(self):
        event = CustomEvent("test", {"foo": 1})
        self.assertEqual(event["foo"], 1)

    def test_getitem_missing_key_raises(self):
        event = CustomEvent("test", {})
        with self.assertRaises(KeyError):
            event["nope"]

    def test_setitem_writes_to_data(self):
        event = CustomEvent("test", {})
        event["foo"] = 42
        self.assertEqual(event.data["foo"], 42)
        self.assertEqual(event["foo"], 42)

    def test_contains(self):
        event = CustomEvent("test", {"foo": 1})
        self.assertIn("foo", event)
        self.assertNotIn("bar", event)

    def test_requires_focus_defaults_false(self):
        self.assertFalse(CustomEvent("test", {}).requires_focus)
        self.assertTrue(CustomEvent("test", {}, requires_focus=True).requires_focus)

    def test_repr_includes_type_and_data(self):
        text = repr(CustomEvent("test", {"foo": 1}))
        self.assertIn("test", text)
        self.assertIn("foo", text)


if __name__ == "__main__":
    unittest.main()