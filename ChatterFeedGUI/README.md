# ChatterFeed

ChatterFeed is a non-commercial art and research project that explores public online conversation as a live data stream.

The application receives messages, classifies the original text, sanitizes a copy for public display, and emits trigger events that can later drive a physical robot arm.

## Raspberry Pi desktop application

Run the graphical application with:

```bash
python3 app.py
```

The GUI uses Python's built-in Tkinter toolkit. On Raspberry Pi OS, if Tkinter is not installed:

```bash
sudo apt install python3-tk
```

The current source is still the built-in mock feed. The application keeps the source, classifier, sanitizer, UI, and robot-control boundary separate so a live Reddit source and physical arm can be added without rewriting the interface.

## Command-line mode

The original terminal version remains available:

```bash
python3 chatterfeed.py
```

## Desktop launcher

`chatterfeed.desktop` is a starter desktop-entry file. Its `Path=` value assumes the project lives at `/home/pi/ChatterFeed`; change that path if the project is installed elsewhere, then copy the file to `~/.local/share/applications/` or the Raspberry Pi desktop.
