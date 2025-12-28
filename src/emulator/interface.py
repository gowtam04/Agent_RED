"""PyBoy emulator interface for Pokemon Red."""

import io
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from pyboy import PyBoy
from pyboy.utils import WindowEvent


class Button(Enum):
    """Game Boy button inputs."""

    A = auto()
    B = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    START = auto()
    SELECT = auto()


class EmulatorInterface:
    """
    Interface for controlling the Pokemon Red game via PyBoy emulator.

    Provides methods for:
    - Button input
    - Frame advancement
    - Screen capture
    - Save/load states
    - Memory reading (delegated to StateReader)
    """

    # Mapping from Button enum to PyBoy window events
    _BUTTON_PRESS_MAP = {
        Button.A: WindowEvent.PRESS_BUTTON_A,
        Button.B: WindowEvent.PRESS_BUTTON_B,
        Button.UP: WindowEvent.PRESS_ARROW_UP,
        Button.DOWN: WindowEvent.PRESS_ARROW_DOWN,
        Button.LEFT: WindowEvent.PRESS_ARROW_LEFT,
        Button.RIGHT: WindowEvent.PRESS_ARROW_RIGHT,
        Button.START: WindowEvent.PRESS_BUTTON_START,
        Button.SELECT: WindowEvent.PRESS_BUTTON_SELECT,
    }

    _BUTTON_RELEASE_MAP = {
        Button.A: WindowEvent.RELEASE_BUTTON_A,
        Button.B: WindowEvent.RELEASE_BUTTON_B,
        Button.UP: WindowEvent.RELEASE_ARROW_UP,
        Button.DOWN: WindowEvent.RELEASE_ARROW_DOWN,
        Button.LEFT: WindowEvent.RELEASE_ARROW_LEFT,
        Button.RIGHT: WindowEvent.RELEASE_ARROW_RIGHT,
        Button.START: WindowEvent.RELEASE_BUTTON_START,
        Button.SELECT: WindowEvent.RELEASE_BUTTON_SELECT,
    }

    def __init__(
        self,
        rom_path: str | Path,
        headless: bool = False,
        speed: int = 1,
        sound: bool = False,
    ):
        """
        Initialize the emulator interface.

        Args:
            rom_path: Path to the Pokemon Red ROM file
            headless: If True, run without display window
            speed: Emulation speed (0=unlimited, 1=normal, 2+=faster)
            sound: If True, enable sound emulation
        """
        rom_path = Path(rom_path)
        if not rom_path.exists():
            raise FileNotFoundError(f"ROM file not found: {rom_path}")

        window_type = "null" if headless else "SDL2"

        self._pyboy = PyBoy(
            str(rom_path),
            window=window_type,
            sound=sound,
        )
        self._pyboy.set_emulation_speed(speed)
        self._frame_count = 0
        self._is_running = True

    @property
    def frame_count(self) -> int:
        """Get the total number of frames elapsed."""
        return self._frame_count

    @property
    def is_running(self) -> bool:
        """Check if the emulator is still running."""
        return self._is_running

    # ─────────────────────────────────────────────────────────
    # FRAME CONTROL
    # ─────────────────────────────────────────────────────────

    def tick(self, frames: int = 1) -> bool:
        """
        Advance the emulator by the specified number of frames.

        Args:
            frames: Number of frames to advance

        Returns:
            True if emulator is still running, False if quit
        """
        for _ in range(frames):
            if not self._pyboy.tick():
                self._is_running = False
                return False
            self._frame_count += 1
        return True

    def run_for_seconds(self, seconds: float) -> bool:
        """
        Run the emulator for approximately the specified duration.

        Args:
            seconds: Duration in seconds (at normal speed)

        Returns:
            True if emulator is still running
        """
        # Game Boy runs at ~60 fps
        frames = int(seconds * 60)
        return self.tick(frames)

    # ─────────────────────────────────────────────────────────
    # INPUT CONTROL
    # ─────────────────────────────────────────────────────────

    def press_button(self, button: Button, hold_frames: int = 8) -> None:
        """
        Press and release a button.

        Args:
            button: The button to press
            hold_frames: How many frames to hold the button (default 8 = ~133ms)
        """
        press_event = self._BUTTON_PRESS_MAP[button]
        release_event = self._BUTTON_RELEASE_MAP[button]

        # Press the button
        self._pyboy.send_input(press_event)

        # Hold for specified frames
        self.tick(hold_frames)

        # Release the button
        self._pyboy.send_input(release_event)

        # Small delay after release for the game to register
        self.tick(4)

    def press_buttons(self, buttons: list[Button], delay_frames: int = 4) -> None:
        """
        Press a sequence of buttons with delays between them.

        Args:
            buttons: List of buttons to press in order
            delay_frames: Frames to wait between button presses
        """
        for button in buttons:
            self.press_button(button)
            self.tick(delay_frames)

    def move(self, direction: str, tiles: int = 1) -> None:
        """
        Move the player in a direction.

        Args:
            direction: "UP", "DOWN", "LEFT", or "RIGHT"
            tiles: Number of tiles to move
        """
        button = Button[direction.upper()]
        for _ in range(tiles):
            # Hold direction longer for movement (~16 frames per tile)
            self.press_button(button, hold_frames=16)
            # Wait for movement animation to complete
            self.tick(8)

    def press_a(self) -> None:
        """Press the A button (confirm/interact)."""
        self.press_button(Button.A)

    def press_b(self) -> None:
        """Press the B button (cancel/back)."""
        self.press_button(Button.B)

    def press_start(self) -> None:
        """Press the Start button (menu)."""
        self.press_button(Button.START)

    # ─────────────────────────────────────────────────────────
    # SCREEN CAPTURE
    # ─────────────────────────────────────────────────────────

    def get_screen(self) -> np.ndarray:
        """
        Get the current screen as a numpy array.

        Returns:
            Screen image as numpy array (144, 160, 3) RGB
        """
        return np.array(self._pyboy.screen.image)

    def get_screen_image(self, scale: int = 3) -> Image.Image:
        """
        Get the current screen as a PIL Image, optionally scaled.

        Args:
            scale: Scale factor (1 = original 160x144, 3 = 480x432)

        Returns:
            PIL Image of the screen
        """
        img = self._pyboy.screen.image.copy()
        if scale != 1:
            new_size = (img.width * scale, img.height * scale)
            img = img.resize(new_size, Image.NEAREST)
        return img

    def get_screen_base64(self, scale: int = 3) -> str:
        """
        Get the screen as a base64-encoded PNG string.

        Args:
            scale: Scale factor for the image

        Returns:
            Base64-encoded PNG string
        """
        import base64

        img = self.get_screen_image(scale)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    # ─────────────────────────────────────────────────────────
    # MEMORY ACCESS
    # ─────────────────────────────────────────────────────────

    def read_memory(self, address: int) -> int:
        """
        Read a single byte from memory.

        Args:
            address: Memory address to read

        Returns:
            Byte value at the address
        """
        return self._pyboy.memory[address]

    def read_memory_word(self, address: int) -> int:
        """
        Read a 16-bit little-endian value from memory.

        Args:
            address: Starting address

        Returns:
            16-bit value
        """
        lo = self.read_memory(address)
        hi = self.read_memory(address + 1)
        return (hi << 8) | lo

    def read_memory_range(self, start: int, length: int) -> bytes:
        """
        Read a range of bytes from memory.

        Args:
            start: Starting address
            length: Number of bytes to read

        Returns:
            Bytes read from memory
        """
        return bytes(self.read_memory(start + i) for i in range(length))

    # ─────────────────────────────────────────────────────────
    # SAVE STATES
    # ─────────────────────────────────────────────────────────

    def save_state(self) -> bytes:
        """
        Create a save state.

        Returns:
            Save state as bytes
        """
        buffer = io.BytesIO()
        self._pyboy.save_state(buffer)
        buffer.seek(0)
        return buffer.read()

    def load_state(self, state: bytes) -> None:
        """
        Load a save state.

        Args:
            state: Save state bytes to load
        """
        buffer = io.BytesIO(state)
        self._pyboy.load_state(buffer)

    def save_state_to_file(self, path: str | Path) -> None:
        """Save state to a file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            self._pyboy.save_state(f)

    def load_state_from_file(self, path: str | Path) -> None:
        """Load state from a file."""
        with open(path, "rb") as f:
            self._pyboy.load_state(f)

    # ─────────────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Clean up and close the emulator."""
        if self._is_running:
            self._pyboy.stop()
            self._is_running = False

    def __enter__(self) -> "EmulatorInterface":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
