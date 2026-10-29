# Jump-Rope Auto-Jumper

**Version 1.1.0**

A small helper that plays the jump-rope minigame for you. It watches the yellow-haired boy, and every time the **"!"** pops up above his head, it presses **F** at the right moment.

![High score: 258 jumps](screenshots/high-score.png)

---

## Install (one time, about 5 minutes)

### 1. Install Python

Python is the free program the bot runs on.

1. Go to **https://www.python.org/downloads/** and click the big yellow **Download Python** button.
2. Open the file you downloaded.
3. ⚠️ **Tick the box "Add python.exe to PATH"** at the bottom of the first screen. The bot won't start if you skip this.
4. Click **Install Now** and wait until it says it's done.

### 2. Download the bot

1. At the top of this page, click the green **Code** button, then **Download ZIP**.
2. Right-click the downloaded ZIP and choose **Extract All…**, then click **Extract**.

---

## Play

1. Open the game and start the **jump-rope minigame**.
2. In the bot folder, **double-click `start.bat`**.
   - The first time, it downloads a few things it needs, which takes about a minute. After that it starts right away.
   - If Windows shows *"Windows protected your PC"*, click **More info**, then **Run anyway**.
3. Click back into the game and press **F8** to turn the bot on.
4. **Do the first jump yourself.** The bot learns from this first "!" and jumps for you from then on.
5. Press **F10** to turn it off when you're done.

### Keys

| Key | What it does |
|---|---|
| **F8** | Turn the bot on / off |
| **F6** | Jump a little **earlier** |
| **F7** | Jump a little **later** |
| **F10** | Quit |

If the boy keeps hitting the rope, press **F6** or **F7** a few times while it runs to fine-tune the timing.

---

## Something not working?

The black bot window shows what it sees:

![Bot window while running](screenshots/console.png)

| You see | What to do |
|---|---|
| **"Python is not installed"** | Do step 1 again and make sure you tick **"Add python.exe to PATH"**. |
| **`boy NOT found`** | Make sure the minigame is on screen. If you use **HDR**, turn it off in the game or Windows display settings. If the game is on a second monitor, see *Advanced* below. |
| **`JUMP` shows, but the boy doesn't jump** | Close the bot, right-click `start.bat`, choose **Run as administrator**. |
| **It stays on `calibrating`** | You need to do the first jump yourself. It needs to see one "!" first. |

---

## Advanced

<details>
<summary>Options, how it works, and running from a terminal</summary>

### Options

Add these after `start.bat` in a terminal, or after `python jumprope_bot.py`:

- `--monitor 1`: watch your second monitor (0 = main screen)
- `--delay 0.18`: start with a different jump delay in seconds (default 0.15)
- `--video clip.mp4`: test the detection on a screen recording

### How it works

1. **Finds the boy** by his yellow hair, the biggest yellow patch on screen. Every half second it re-checks the whole screen so it doesn't get stuck on the yellow lanterns.
2. **Watches for the "!"** above his head by comparing it to `bubble.png`.
3. **Presses F** 0.15 seconds after the "!" appears, the same timing a person's successful jumps use.
4. **Adjusts to your screen size** from the first "!" it sees (`scale locked at …`).

### Run without start.bat

```bash
pip install -r requirements.txt
python jumprope_bot.py
```

### Tested on

- Windows, 2560×1440 fullscreen
- Recordings shrunk to 70% and enlarged to 125%. Very small resolutions (about 720p) may not work.

</details>
