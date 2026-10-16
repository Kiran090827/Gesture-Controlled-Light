"""Control a nikki.build Streams phone flashlight with hand gestures."""

from __future__ import annotations

import asyncio
from getpass import getpass
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
from nikki_streams import SDK


PHONE_ADDRESS = os.getenv("NIKKI_PHONE_ADDRESS", "10.172.21.252:3000")
SESSION_ID = os.getenv("NIKKI_SESSION_ID", "").strip()
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
PINCH_RATIO = float(os.getenv("PINCH_RATIO", "0.34"))
SPREAD_RATIO = float(os.getenv("SPREAD_RATIO", "0.55"))
STABLE_FRAMES = int(os.getenv("STABLE_FRAMES", "4"))
MIN_COMMAND_INTERVAL = 0.7
MODEL_PATH = Path(__file__).resolve().parent / "models" / "hand_landmarker.task"
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)


@dataclass
class GestureFilter:
    """Require a gesture to remain stable before acting on it."""

    candidate: str | None = None
    count: int = 0
    stable: str | None = None

    def update(self, gesture: str | None) -> str | None:
        if gesture is None:
            self.candidate = None
            self.count = 0
            return None
        if gesture == self.candidate:
            self.count += 1
        else:
            self.candidate = gesture
            self.count = 1
        if self.count >= STABLE_FRAMES and gesture != self.stable:
            self.stable = gesture
            return gesture
        return None


def hand_gesture(hand: Any) -> tuple[str | None, float]:
    """Classify pinch/spread using index-tip/thumb-tip distance vs palm width."""
    points = hand
    thumb = points[4]
    index = points[8]
    # Hand-size normalization makes the threshold mostly independent of distance.
    palm_width = ((points[5].x - points[17].x) ** 2 + (points[5].y - points[17].y) ** 2) ** 0.5
    if palm_width < 1e-6:
        return None, 0.0
    ratio = (((thumb.x - index.x) ** 2 + (thumb.y - index.y) ** 2) ** 0.5) / palm_width
    if ratio <= PINCH_RATIO:
        return "pinch", ratio
    if ratio >= SPREAD_RATIO:
        return "spread", ratio
    return None, ratio


def event_callback(event: Any) -> None:
    """Print Streams connection state and phone sensor events."""
    if getattr(event, "type", None) == "statusChange":
        print(f"[Streams] Connection: {event.data}")
        error = getattr(event, "error", None)
        if error:
            print(f"[Streams] Connection detail: {error!r}")
    elif getattr(event, "type", None) == "data":
        print(f"[Streams] Phone data: {event.data}")
    else:
        print(f"[Streams] Event: {event}")


async def ensure_connected(device: Any, connection_lock: asyncio.Lock) -> bool:
    """Connect once at a time; return False after a failed attempt."""
    async with connection_lock:
        if device.is_connected:
            return True
        try:
            await device.connect()
            return device.is_connected
        except Exception as exc:
            print(f"[Streams] Reconnect failed: {exc}")
            return False


async def reconnect_while_running(device: Any, connection_lock: asyncio.Lock) -> None:
    """Keep trying with bounded backoff while the camera loop is active."""
    delay = 1.0
    while True:
        if not device.is_connected:
            if await ensure_connected(device, connection_lock):
                delay = 1.0
            else:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 15.0)
                continue
        await asyncio.sleep(1.0)


async def connect_until_ready(device: Any, connection_lock: asyncio.Lock) -> None:
    """Keep trying the initial connection until Streams is available."""
    delay = 1.0
    while not await ensure_connected(device, connection_lock):
        print(f"[Streams] Waiting for the phone; retrying in {delay:g}s. Keep the Streams session open.")
        await asyncio.sleep(delay)
        delay = min(delay * 2, 15.0)


async def run_camera(device: Any, connection_lock: asyncio.Lock) -> None:
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        raise RuntimeError(
            f"Could not open camera {CAMERA_INDEX}. Close other camera apps or set CAMERA_INDEX."
        )

    if not MODEL_PATH.is_file():
        raise RuntimeError(f"Hand landmark model is missing: {MODEL_PATH}")
    vision = mp.tasks.vision
    options = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        # Webcam lighting and classroom cameras can be noisy. Start with a
        # moderately permissive detector; gesture stability filters commands.
        min_hand_detection_confidence=0.4,
        min_hand_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    gesture_filter = GestureFilter()
    light_on: bool | None = None
    haptic_pending = False
    last_command_at = 0.0
    last_observed_state: str | None = None
    camera_warning_printed = False

    print("Camera ready. Show your full hand, palm toward the webcam, in a well-lit area.")
    print("Pinch to switch the phone light off; spread thumb and index finger to switch it on.")
    print("Press Esc or Q in the camera window to quit.")
    try:
        with vision.HandLandmarker.create_from_options(options) as hands:
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Camera frame was unavailable; retrying.")
                    await asyncio.sleep(0.05)
                    continue

                # Some Windows privacy shutters/drivers return a black frame
                # with a crossed-camera icon instead of failing to open.
                camera_blocked = float(frame.mean()) < 14 and float(frame.std()) < 20
                if camera_blocked and not camera_warning_printed:
                    print("[Camera] Frames are nearly black. Open the webcam privacy shutter and allow desktop apps to use the camera.")
                    camera_warning_printed = True
                elif not camera_blocked:
                    camera_warning_printed = False

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = int(time.monotonic() * 1000)
                result = hands.detect_for_video(mp_image, timestamp_ms)
                label = "Camera blocked or too dark" if camera_blocked else "Show one hand"
                observed_state = "no hand"
                if result.hand_landmarks:
                    hand = result.hand_landmarks[0]
                    height, width = frame.shape[:2]
                    for start, end in HAND_CONNECTIONS:
                        a, b = hand[start], hand[end]
                        cv2.line(frame, (int(a.x * width), int(a.y * height)),
                                 (int(b.x * width), int(b.y * height)), (70, 220, 120), 2)
                    for point in hand:
                        cv2.circle(frame, (int(point.x * width), int(point.y * height)), 4, (30, 80, 255), -1)
                    gesture, ratio = hand_gesture(hand)
                    observed_state = gesture or "between gesture thresholds"
                    command = gesture_filter.update(gesture)
                    label = f"{gesture or 'Move to pinch/spread'}  ratio={ratio:.2f}"
                    if observed_state != last_observed_state:
                        print(f"[Camera] {observed_state}; normalized finger distance={ratio:.2f}")
                        last_observed_state = observed_state

                    if command and time.monotonic() - last_command_at >= MIN_COMMAND_INTERVAL:
                        desired_on = command == "spread"
                        last_command_at = time.monotonic()
                        if desired_on != light_on:
                            try:
                                if not await ensure_connected(device, connection_lock):
                                    gesture_filter.stable = None
                                    raise ConnectionError("Streams is offline; retrying automatically.")
                                await device.set_light_status(desired_on)
                                light_on = desired_on
                                haptic_pending = True
                            except Exception as exc:
                                print(f"Could not control the phone light: {exc}")
                                gesture_filter.stable = None
                                label = "Phone command failed; check Streams connection"
                        if light_on == desired_on and haptic_pending:
                            try:
                                if not await ensure_connected(device, connection_lock):
                                    gesture_filter.stable = None
                                    raise ConnectionError("Streams is offline; retrying automatically.")
                                await device.set_haptic()
                                haptic_pending = False
                                label = f"ON command sent" if desired_on else "OFF command sent"
                                print(
                                    f"Gesture {command}: sent flashlight {'ON' if desired_on else 'OFF'} command "
                                    "and haptic request (Streams SDK provides no phone-side acknowledgement)."
                                )
                            except Exception as exc:
                                print(f"Light command sent, but vibration failed: {exc}")
                                gesture_filter.stable = None
                                label = "Light command sent; haptic request will retry"
                        elif desired_on == light_on and not haptic_pending:
                            label = f"Light already {'ON' if light_on else 'OFF'}"

                if observed_state == "no hand" and last_observed_state != observed_state:
                    print("[Camera] No hand detected.")
                    last_observed_state = observed_state

                cv2.putText(frame, label, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (40, 230, 100), 2)
                cv2.putText(frame, "Pinch = OFF   Spread = ON   |   Q/Esc = quit", (18, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.imshow("Gesture-Controlled Phone Light", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q"), ord("Q")):
                    break
                # Yield to the Streams asyncio client and keep the UI responsive.
                await asyncio.sleep(0.001)
    finally:
        camera.release()
        cv2.destroyAllWindows()


async def main() -> None:
    session_id = SESSION_ID or getpass("Streams Session ID (input hidden): ").strip()
    if not session_id:
        raise SystemExit("A Streams Session ID is required.")
    SDK.initialize(session_id)
    device = SDK.create_device(PHONE_ADDRESS, event_callback)
    connection_lock = asyncio.Lock()
    print(f"Connecting to Streams phone at {PHONE_ADDRESS} ...")
    try:
        await connect_until_ready(device, connection_lock)
        reconnect_task = asyncio.create_task(reconnect_while_running(device, connection_lock))
        try:
            await run_camera(device, connection_lock)
        finally:
            reconnect_task.cancel()
            try:
                await reconnect_task
            except asyncio.CancelledError:
                pass
    finally:
        try:
            await device.disconnect()
        except Exception as exc:
            print(f"Streams disconnect notice: {exc}")
        print("Disconnected. The phone flashlight is left in its last commanded state.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as exc:
        print(f"Startup/runtime error: {exc}", file=sys.stderr)
        raise
