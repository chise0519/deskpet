from deskpet import main


class FakeTray:
    def __init__(self):
        self.messages = []

    def showMessage(self, *args):
        self.messages.append(args)


class FakePet:
    def clear_alert(self):
        pass


def test_startup_check_marks_once_and_recurring(monkeypatch):
    once = {"id": 1, "content": "一次", "repeat": "once", "due_at": "2026-01-01T09:00:00"}
    daily = {"id": 2, "content": "每天", "repeat": "daily", "due_at": "2026-01-01T10:00:00"}
    monkeypatch.setattr(main.storage, "list_reminders", lambda: [once, daily])
    monkeypatch.setattr(main.scheduler, "due_reminders", lambda _rows, _now: [once, daily])
    monkeypatch.setattr(
        main.scheduler,
        "next_after_trigger",
        lambda reminder, _now: None if reminder["repeat"] == "once" else "next",
    )
    calls = []
    monkeypatch.setattr(
        main.storage,
        "mark_notified",
        lambda reminder_id, _now, nxt: calls.append((reminder_id, nxt)),
    )
    fake = type("FakeApp", (), {"tray": FakeTray()})()
    main.DeskPetApp._startup_check(fake)
    assert calls == [(1, None), (2, "next")]
    assert len(fake.tray.messages) == 1


def test_snooze_uses_separate_field(monkeypatch):
    monkeypatch.setattr(main.storage, "list_reminders", lambda: [{"id": 7}])
    updates = []
    monkeypatch.setattr(
        main.storage,
        "update_reminder",
        lambda reminder_id, **fields: updates.append((reminder_id, fields)),
    )
    fake = type("FakeApp", (), {"pet": FakePet()})()
    main.DeskPetApp._alert_snooze(fake, 7)
    assert updates[0][0] == 7
    assert "snoozed_until" in updates[0][1]
    assert "due_at" not in updates[0][1]
