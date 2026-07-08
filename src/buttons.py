import logging
import threading

log = logging.getLogger(__name__)

BUTTON_GPIO = [5, 6, 25, 24]
BUTTON_LABELS = ["A", "B", "C", "D"]

_SATURATION_MIN = 0.2
_SATURATION_MAX = 1.0
_SATURATION_STEP = 0.1


class ButtonMonitor:
    def __init__(self, state):
        self._state = state
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._running = False

    def _run(self):
        import gpiod
        import gpiodevice
        from gpiod.line import Bias, Direction, Edge

        chip = gpiodevice.find_chip_by_platform()

        INPUT = gpiod.LineSettings(
            direction=Direction.INPUT,
            bias=Bias.PULL_UP,
            edge_detection=Edge.FALLING,
        )

        offsets = [chip.line_offset_from_id(pin) for pin in BUTTON_GPIO]
        line_config = dict.fromkeys(offsets, INPUT)
        request = chip.request_lines(
            consumer="birdnet-eink-buttons", config=line_config
        )

        log.info(
            "Button monitor started (A=GPIO%d, B=GPIO%d, C=GPIO%d, D=GPIO%d)",
            *BUTTON_GPIO,
        )

        import datetime as _dt

        while self._running:
            if request.wait_edge_events(timeout=_dt.timedelta(seconds=1)):
                for event in request.read_edge_events():
                    idx = offsets.index(event.line_offset)
                    label = BUTTON_LABELS[idx]
                    self._handle(label)

    def _handle(self, label):
        state = self._state
        if label == "A":
            state["force_refresh_once"] = True
            state["wake_event"].set()
            log.info("Button A: force refresh")
        elif label == "B":
            state["saturation"] = round(
                max(_SATURATION_MIN, state["saturation"] - _SATURATION_STEP), 1
            )
            state["force_refresh_once"] = True
            state["wake_event"].set()
            log.info("Button B: saturation decreased to %.1f", state["saturation"])
        elif label == "C":
            state["saturation"] = round(
                min(_SATURATION_MAX, state["saturation"] + _SATURATION_STEP), 1
            )
            state["force_refresh_once"] = True
            state["wake_event"].set()
            log.info("Button C: saturation increased to %.1f", state["saturation"])
        elif label == "D":
            state["clear_requested"] = True
            state["force_refresh_once"] = True
            state["wake_event"].set()
            log.info("Button D: clear and refresh")
