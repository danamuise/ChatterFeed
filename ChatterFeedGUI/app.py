import queue
import threading
import tkinter as tk
from tkinter import ttk

from core import ChatterFeedEngine, ProcessedMessage
from sources.mock_source import MockSource


class ChatterFeedApp(tk.Tk):
    POLL_MS = 100

    def __init__(self) -> None:
        super().__init__()
        self.title("ChatterFeed")
        self.geometry("960x680")
        self.minsize(760, 560)

        self.engine = ChatterFeedEngine()
        self.source = MockSource()
        self.events: queue.Queue[ProcessedMessage | tuple[str, str]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None

        self.status_var = tk.StringVar(value="OFF")
        self.robot_var = tk.StringVar(value="Simulation mode")
        self.feed_active = False
        self.dot_on = False

        self._build_ui()
        self.after(500, self._blink_status_dot)
        self.after(self.POLL_MS, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))

        title = ttk.Label(header, text="CHATTERFEED", font=("TkDefaultFont", 24, "bold"))
        title.pack(side="left")

        self.status_label = ttk.Label(
            header,
            textvariable=self.status_var,
            font=("TkDefaultFont", 12, "bold"),
        )
        self.status_label.pack(side="left", padx=(24, 6))

        self.status_dot = tk.Label(
            header,
            text="●",
            font=("TkDefaultFont", 16, "bold"),
            fg="#d22",
            bg="#111111",
            borderwidth=0,
        )
        self.status_dot.pack(side="left")

        message_frame = ttk.LabelFrame(outer, text="Live Feed", padding=10)
        message_frame.pack(fill="both", expand=True)

        feed_container = ttk.Frame(message_frame)
        feed_container.pack(fill="both", expand=True)

        self.message = tk.Text(
            feed_container,
            wrap="word",
            height=12,
            font=("TkFixedFont", 13),
            relief="flat",
            padx=8,
            pady=8,
            bg="#0d0d0d",
            fg="#f2f2f2",
            insertbackground="#f2f2f2",
            selectbackground="#3a3a3a",
            selectforeground="#ffffff",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            feed_container,
            orient="vertical",
            command=self.message.yview,
        )
        self.message.configure(yscrollcommand=scrollbar.set)
        self.message.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.message.tag_configure("trigger", font=("TkFixedFont", 13, "bold"), foreground="#ff6b6b")
        self.message.tag_configure("meta", font=("TkFixedFont", 11), foreground="#9a9a9a")
        self.message.configure(state="disabled")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(14, 0))

        self.start_button = ttk.Button(controls, text="Start", command=self.start)
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

        ttk.Button(controls, text="Test Robot", command=self.test_robot).pack(side="left", padx=(8, 0))

        ttk.Label(controls, textvariable=self.robot_var).pack(side="right")

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        self.stop_event.clear()
        self.worker = threading.Thread(target=self._stream_worker, daemon=True)
        self.worker.start()
        self.feed_active = True
        self.status_var.set("LIVE")
        self.dot_on = True
        self._update_status_dot()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def stop(self) -> None:
        self.stop_event.set()
        self.feed_active = False
        self.status_var.set("OFF")
        self.dot_on = False
        self._update_status_dot()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def test_robot(self) -> None:
        self.robot_var.set(self.engine.robot.test())

    def _stream_worker(self) -> None:
        try:
            for message in self.source.stream():
                if self.stop_event.is_set():
                    break
                self.events.put(self.engine.process(message))
        except Exception as exc:  # UI should survive a source failure.
            self.events.put(("error", str(exc)))

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if isinstance(event, tuple):
                    kind, text = event
                    if kind == "error":
                        self.feed_active = False
                        self.status_var.set("ERROR")
                        self.dot_on = False
                        self._update_status_dot()
                        self.robot_var.set(text)
                        self.start_button.configure(state="normal")
                        self.stop_button.configure(state="disabled")
                else:
                    self._show_message(event)
        except queue.Empty:
            pass

        self.after(self.POLL_MS, self._drain_events)

    def _update_status_dot(self) -> None:
        if self.feed_active:
            color = "#00d82f" if self.dot_on else "#166b2c"
        else:
            color = "#d22"

        self.status_dot.configure(fg=color)

    def _blink_status_dot(self) -> None:
        if self.feed_active:
            self.dot_on = not self.dot_on
        else:
            self.dot_on = False

        self._update_status_dot()
        self.after(500, self._blink_status_dot)

    def _show_message(self, item: ProcessedMessage) -> None:
        self.message.configure(state="normal")

        self.message.insert("end", "=" * 70 + "\n", "meta")
        self.message.insert("end", f"Subreddit: {item.source}\n", "meta")
        self.message.insert("end", f"Message Subject: {item.subject}\n", "meta")
        self.message.insert("end", f"Time:   {item.timestamp}\n", "meta")

        for category in item.classification.categories:
            label = category.replace("_", " ").upper()
            self.message.insert("end", f"[TRIGGER] {label}\n", "trigger")

        self.message.insert("end", "\n")
        self.message.insert("end", item.safe_text + "\n\n")
        self.message.see("end")
        self.message.configure(state="disabled")

    def _on_close(self) -> None:
        self.stop_event.set()
        self.destroy()


def main() -> None:
    ChatterFeedApp().mainloop()


if __name__ == "__main__":
    main()
