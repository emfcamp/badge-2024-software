import asyncio
import unittest

from system.eventbus import _EventBus, _matches, _type_name
from events import Event
from events.custom import CustomEvent


class DummyEvent(Event):
    pass


class OtherEvent(Event):
    pass


class App:
    """Minimal stand-in for an app."""

    def __init__(self, focused=True):
        self._focused = focused


async def drive(bus, events):
    """Run the bus long enough to process ``events``, then stop it."""
    task = asyncio.create_task(bus.run())
    for event in events:
        bus.emit(event)
    # Yield repeatedly so run() can drain the queue and schedule handlers.
    for _ in range(20):
        await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class MatchesTest(unittest.TestCase):
    def test_class_matches_by_isinstance(self):
        self.assertTrue(_matches(DummyEvent(), DummyEvent))
        self.assertFalse(_matches(OtherEvent(), DummyEvent))

    def test_string_matches_custom_event_type(self):
        self.assertTrue(_matches(CustomEvent("test", {}), "test"))
        self.assertFalse(_matches(CustomEvent("other", {}), "test"))

    def test_string_matches_dict_type_field(self):
        self.assertTrue(_matches({"type": "test"}, "test"))
        self.assertFalse(_matches({"type": "other"}, "test"))
        self.assertFalse(_matches({}, "test"))

    def test_string_does_not_match_plain_object(self):
        self.assertFalse(_matches(DummyEvent(), "test"))


class TypeNameTest(unittest.TestCase):
    def test_class_uses_dunder_name(self):
        self.assertEqual(_type_name(DummyEvent), "DummyEvent")

    def test_string_is_returned_as_is(self):
        self.assertEqual(_type_name("test"), "test")


class EventBusDispatchTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bus = _EventBus()
        self.received = []
        self.app = App()

    def handler(self, event):
        self.received.append(event)

    async def test_class_registration_still_works(self):
        self.bus.on(DummyEvent, self.handler, self.app)
        event = DummyEvent()
        await drive(self.bus, [event, OtherEvent()])
        self.assertEqual(self.received, [event])

    async def test_custom_event_by_string_type(self):
        self.bus.on("test", self.handler, self.app)
        event = CustomEvent("test", {"foo": 1})
        await drive(self.bus, [event, CustomEvent("other", {})])
        self.assertEqual(self.received, [event])

    async def test_dict_event_by_string_type(self):
        self.bus.on("test", self.handler, self.app)
        event = {"type": "test", "foo": 1}
        await drive(self.bus, [event, {"type": "other"}])
        self.assertEqual(self.received, [event])

    async def test_dict_class_receives_all_dict_events(self):
        # Registering on the ``dict`` class (rather than a string type) should
        # match every dict event regardless of its "type" field.
        self.bus.on(dict, self.handler, self.app)
        events = [{"type": "test"}, {"type": "other"}, {"no_type": 1}]
        await drive(self.bus, events + [CustomEvent("test", {})])
        self.assertEqual(self.received, events)

    async def test_typeless_dict_ignored_by_string_subscriber(self):
        # A dict without a "type" key has no type to match, so a string
        # subscription never receives it (dict.get("type") is None).
        self.bus.on("test", self.handler, self.app)
        await drive(self.bus, [{"no_type": 1}, {"type": None}])
        self.assertEqual(self.received, [])

    async def test_typeless_dict_still_reaches_dict_class_subscriber(self):
        # Subscribing on the dict class ignores "type" entirely, so a typeless
        # dict is still delivered.
        self.bus.on(dict, self.handler, self.app)
        event = {"no_type": 1}
        await drive(self.bus, [event])
        self.assertEqual(self.received, [event])

    async def test_async_handler(self):
        async def async_handler(event):
            self.received.append(event)

        self.bus.on_async("test", async_handler, self.app)
        event = CustomEvent("test", {})
        await drive(self.bus, [event])
        self.assertEqual(self.received, [event])

    async def test_remove_stops_delivery(self):
        self.bus.on("test", self.handler, self.app)
        self.bus.remove("test", self.handler, self.app)
        await drive(self.bus, [CustomEvent("test", {})])
        self.assertEqual(self.received, [])

    async def test_deregister_removes_app(self):
        self.bus.on("test", self.handler, self.app)
        self.bus.deregister(self.app)
        await drive(self.bus, [CustomEvent("test", {})])
        self.assertEqual(self.received, [])


class EventBusFocusTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bus = _EventBus()
        self.received = []

    def handler(self, event):
        self.received.append(event)

    async def test_focus_required_dict_skips_unfocused_app(self):
        self.bus.on("test", self.handler, App(focused=False))
        await drive(self.bus, [{"type": "test", "requires_focus": True}])
        self.assertEqual(self.received, [])

    async def test_focus_required_dict_reaches_focused_app(self):
        self.bus.on("test", self.handler, App(focused=True))
        event = {"type": "test", "requires_focus": True}
        await drive(self.bus, [event])
        self.assertEqual(self.received, [event])

    async def test_no_focus_required_reaches_unfocused_app(self):
        self.bus.on("test", self.handler, App(focused=False))
        event = {"type": "test"}
        await drive(self.bus, [event])
        self.assertEqual(self.received, [event])

    async def test_custom_event_requires_focus_attribute(self):
        self.bus.on("test", self.handler, App(focused=False))
        await drive(self.bus, [CustomEvent("test", {}, requires_focus=True)])
        self.assertEqual(self.received, [])