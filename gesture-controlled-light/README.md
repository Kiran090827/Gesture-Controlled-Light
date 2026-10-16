# Gesture-Controlled Phone Light

Use a webcam and MediaPipe hand tracking to control an Android phone's flashlight through the nikki.build Streams Python SDK. Pinch your thumb and index finger together to turn the flashlight off; spread them apart to turn it on. The phone vibrates after each successful light command.

## Requirements

- Android phone running the Streams app, with flashlight and haptics available
- Phone and computer on the same Wi-Fi/LAN
- Python 3.10 or newer (64-bit Python recommended on Windows)
- Webcam
- A Streams session ID from the Streams app

## Install on Windows

For a guided launch, open PowerShell in this project folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

The launcher creates `.venv` if needed, installs the pinned dependencies, starts the app, and leaves the window open to show any errors. You can also install and activate the environment manually:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

If `py` is not recognized, install 64-bit Python 3.12 from python.org, enable the Python launcher during setup, then reopen PowerShell. The project requires Python 3.10 or newer.

If PowerShell blocks activation, run the environment's Python directly instead:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Connect to Streams

1. Open nikki.build Streams on the phone and create or open the session you want to use.
2. Join that session from the Android phone and make sure the flashlight and haptic services are enabled/available.
3. Keep the phone and computer on the same local network. The supplied phone server is `10.172.21.252:3000`.
4. Have the **Streams Session ID** from the app ready. This is separate from the WebSocket address. Keep it private.
5. In PowerShell, launch the program:

```powershell
$env:NIKKI_PHONE_ADDRESS = "10.172.21.252:3000"
python main.py
```

When prompted, type or paste the Session ID; the input is hidden and is not saved. You may set `$env:NIKKI_SESSION_ID` instead if you prefer. The nikki Streams SDK builds the WebSocket URL from the address and initialized session ID. Enter the address as `host:port` (without `ws://`) as required by the guide. The hand landmark model is included in `models/hand_landmarker.task`, so first launch does not need to download a model.

To check phone control without the webcam or gesture logic, run this optional direct SDK check from the same folder:

```powershell
.venv\Scripts\python.exe .\streams_smoke_test.py
```

It sends ON plus haptic, waits three seconds, then sends OFF plus haptic. Watch the phone during the sequence. The SDK reports WebSocket send errors, but it does not receive acknowledgements that the phone applied the commands.

`.env.example` is a reference for environment variable names; this project does not load `.env` files automatically. Set optional values in PowerShell with `$env:CAMERA_INDEX = "1"`, for example.

## Use the gestures

- Hold one hand where the webcam can see it.
- Pinch thumb and index fingertips together to command **OFF**.
- Spread thumb and index fingertips apart to command **ON**.
- Keep the gesture steady for a few frames. The window shows the detected ratio and status.
- Press `Q` or `Esc` in the camera window to stop.

Each state transition sends one flashlight command followed by one vibration request. Holding the same gesture does not repeatedly send commands. The SDK does not provide a phone-side acknowledgement, so a successful send in the terminal does not prove the phone acted; check the phone's flashlight and haptics. On exit, the light remains in its last commanded state if the phone applied the command.

## How it works

1. OpenCV reads webcam frames and mirrors them for a natural preview.
2. MediaPipe Tasks detects hand landmarks, including the thumb tip (landmark 4), index tip (8), and palm-width reference points (5 and 17).
3. The program measures the thumb-to-index distance and divides it by palm width. This normalized ratio compensates for the hand appearing larger or smaller in the image.
4. A stable pinch (`ratio <= 0.34`) means OFF; a stable spread (`ratio >= 0.55`) means ON. The gap between thresholds prevents flicker, and four stable frames filter brief misdetections.
5. The async Streams SDK sends `device.set_light_status(True/False)` to the phone and then sends a `device.set_haptic()` request when the commanded state changes. These calls confirm only that data was sent through the WebSocket; the SDK does not report whether Android applied the command.

## Troubleshooting

- **Session ID missing:** Enter the Session ID when the hidden prompt appears, or set `$env:NIKKI_SESSION_ID` in the same PowerShell window before starting.
- **Cannot connect:** Confirm the phone and PC are on the same network, the Streams session is active, the phone has joined it, and the address/port is current. Check that Windows Firewall permits Python on the private network.
- **Connection drops or times out:** Keep the Streams app open in the foreground and confirm the session is still active. The program retries its initial connection and reconnects automatically if the socket drops.
- **Camera unavailable:** Close apps using the webcam or set `$env:CAMERA_INDEX = "1"` (try other indexes if needed).
- **Preview is black or shows a crossed-out camera:** Open the webcam's physical privacy shutter, then check Windows **Settings → Privacy & security → Camera** and allow desktop apps to access it. Restart the project afterward. The app also flags nearly black frames in its preview.
- **No hand detected:** Make sure the preview shows a live image (not a black frame), use bright even lighting, face your palm toward the webcam, and keep your full hand inside the frame.
- **Gesture thresholds feel wrong:** Adjust `PINCH_RATIO`, `SPREAD_RATIO`, and `STABLE_FRAMES` in the environment. Keep the spread threshold above the pinch threshold.
- **Phone does not react:** Confirm the phone is still joined to the same active session, and that flashlight and haptics services/permissions are enabled in Streams and Android. Then change gestures (pinch, then spread) to send fresh commands. Streams' Python SDK sends commands without a phone-side acknowledgement, so check the phone itself to verify each action.

## Project files

- `main.py` — webcam, gesture recognition, and Streams control loop
- `streams_smoke_test.py` — optional direct flashlight/haptic connection check
- `run.ps1` — Windows launcher that prepares dependencies and keeps output visible
- `requirements.txt` — pinned Python dependencies, including the MediaPipe Tasks API used by the program
- `models/hand_landmarker.task` — bundled MediaPipe hand landmark model
- `MODEL_LICENSE.txt` — model source and license attribution
- `.gitignore` — excludes local environments and secret configuration from source control
- `.env.example` — configuration template
- `README.md` — installation, connection, usage, and explanation

## References

The supplied nikki.build guide is **Streams with Python**. It documents `nikki-streams`, Python 3.10+, session initialization, the `host:port` device address, asynchronous connection, flashlight control, and haptic feedback. Its example uses `SDK.initialize(...)`, `SDK.create_device(...)`, `device.connect()`, `device.set_light_status(...)`, `device.set_haptic()`, and `device.disconnect()`. MediaPipe Tasks follows Google's [Hand Landmarker Python guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python) and uses a model file distributed with this project.
