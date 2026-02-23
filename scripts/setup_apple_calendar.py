"""Set up Apple Calendar access for Istari.

Run this script once to trigger the macOS permission dialog. After
granting access, the Istari backend can read your Calendar.app events
(including iCloud, Google Calendar, Exchange, and any other synced source).

Usage:
    source backend/.venv/bin/activate
    pip install -e "backend/.[apple]"
    python scripts/setup_apple_calendar.py
"""

import sys
import time
import threading


def main() -> None:
    try:
        import EventKit  # type: ignore[import-untyped]
    except ImportError:
        print("Error: pyobjc-framework-EventKit is not installed.")
        print("Run: pip install -e 'backend/.[apple]'")
        sys.exit(1)

    print("Checking Apple Calendar authorization status...")

    store = EventKit.EKEventStore.alloc().init()
    status = int(EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeEvent
    ))

    STATUS_LABELS = {
        0: "Not Determined",
        1: "Restricted",
        2: "Denied",
        3: "Authorized / Full Access",
        4: "Write Only",
    }
    print(f"Current status: {STATUS_LABELS.get(status, str(status))}")

    if status == 3:
        print("\nCalendar access is already granted. Istari is ready to read your calendar.")
        _list_calendars(store, EventKit)
        return

    if status == 2:
        print(
            "\nCalendar access is DENIED.\n"
            "Open System Settings → Privacy & Security → Calendars\n"
            "and enable access for Terminal (or Python)."
        )
        sys.exit(1)

    if status == 1:
        print("\nCalendar access is restricted by a device management policy.")
        sys.exit(1)

    # status == 0: request access
    print("\nRequesting calendar access — approve the dialog that appears...")

    result: list[bool] = [False]
    done = threading.Event()

    def handler(granted: bool, error: object) -> None:
        result[0] = bool(granted)
        done.set()

    if hasattr(store, "requestFullAccessToEventsWithCompletion_"):
        store.requestFullAccessToEventsWithCompletion_(handler)
    else:
        store.requestAccessToEntityType_completion_(EventKit.EKEntityTypeEvent, handler)

    # Pump the RunLoop — the TCC callback is delivered via RunLoop,
    # so blocking with done.wait() prevents it from ever firing.
    import Foundation  # type: ignore[import-untyped]
    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = time.monotonic() + 30
    while not done.is_set() and time.monotonic() < deadline:
        run_loop.runUntilDate_(Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.1))

    if result[0]:
        print("\nAccess granted! Istari can now read your calendar.")
        _list_calendars(store, EventKit)
    else:
        print(
            "\nAccess was not granted. Check System Settings → "
            "Privacy & Security → Calendars."
        )
        sys.exit(1)


def _list_calendars(store: object, ek: object) -> None:
    """Print the list of accessible calendars as a sanity check."""
    try:
        calendars = store.calendarsForEntityType_(ek.EKEntityTypeEvent)  # type: ignore[attr-defined]
        if calendars:
            print(f"\nAccessible calendars ({len(calendars)}):")
            for cal in calendars:
                print(f"  - {cal.title()} [{cal.source().title()}]")
    except Exception as exc:
        print(f"(Could not list calendars: {exc})")


if __name__ == "__main__":
    main()
