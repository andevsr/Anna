# macOS permissions required by anna

The app needs three permissions granted to whichever program runs it (Terminal, iTerm, VS Code, or the bundled `.app`).

## 1. Accessibility (mouse + keyboard control)
System Settings → Privacy & Security → **Accessibility** → enable the toggle for your terminal/app.

## 2. Screen Recording (screenshots)
System Settings → Privacy & Security → **Screen Recording** → enable the toggle for your terminal/app.

> Both of the above usually require **restarting** the terminal app after enabling.

## 3. Microphone (needed in phase 3, for voice)
System Settings → Privacy & Security → **Microphone** → enable for your terminal/app.

## Verify
```bash
# 1. Screen capture works (writes /tmp/anna_test.png)
uv run python -c "from anna.control.screen import capture; capture().image.save('/tmp/anna_test.png'); print('ok')"

# 2. Synthetic mouse move works (cursor should jump to top-left, then back)
uv run python -c "from anna.control import mouse; mouse.move(100,100); import time; time.sleep(0.3); mouse.move(200,200)"
```

If the mouse doesn't move or the screenshot is blank/black, re-check the Accessibility / Screen Recording toggles and restart the terminal.
