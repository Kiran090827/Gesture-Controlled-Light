"""Send one direct ON/OFF and haptic sequence to verify Streams control."""

from __future__ import annotations

import asyncio
from getpass import getpass

from nikki_streams import SDK


PHONE_ADDRESS = "10.172.21.252:3000"


def callback(event: object) -> None:
    if getattr(event, "type", None) == "statusChange":
        print(f"[Streams] Connection: {getattr(event, 'data', 'unknown')}")
        error = getattr(event, "error", None)
        if error:
            print(f"[Streams] Connection detail: {error!r}")


async def main() -> None:
    session_id = getpass("Streams Session ID (input hidden): ").strip()
    if not session_id:
        raise SystemExit("A Streams Session ID is required.")

    SDK.initialize(session_id)
    device = SDK.create_device(PHONE_ADDRESS, callback)
    try:
        await device.connect()
        print("Sending flashlight ON and 500 ms haptic request; watch the phone.")
        await device.set_light_status(True)
        await device.set_haptic(500)
        await asyncio.sleep(3)
        print("Sending flashlight OFF and 500 ms haptic request.")
        await device.set_light_status(False)
        await device.set_haptic(500)
        print("Sequence sent. The SDK does not report phone-side command acknowledgements.")
    finally:
        await device.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
