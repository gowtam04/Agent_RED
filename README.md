# Pokemon Red AI Agent

An AI agent that plays Pokemon Red using Claude. This MVP demonstrates Claude controlling a Game Boy emulator via the PyBoy library.

## Features

- **PyBoy Integration**: Runs Pokemon Red in a visible emulator window
- **Memory Reading**: Extracts game state (position, party, battles, badges) from memory
- **Claude Agent**: Makes decisions based on game state using tool calling
- **Auto-Checkpoints**: Periodic save states for recovery

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- SDL2 library (for PyBoy display)
- Anthropic API key
- Pokemon Red ROM file (you must provide your own)

### Installing SDL2

**macOS:**
```bash
brew install sdl2
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libsdl2-dev
```

**Windows:**
SDL2 is typically bundled with PyBoy on Windows.

## Setup

1. **Clone and enter the project:**
   ```bash
   cd Project_RED
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

4. **Add your ROM file:**
   ```bash
   cp /path/to/pokemon_red.gb roms/pokemon_red.gb
   ```

## Running

```bash
poetry run python -m src.main
```

Or using the script alias:
```bash
poetry run pokemon-agent
```

### Configuration Options

Edit `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `ROM_PATH` | `roms/pokemon_red.gb` | Path to ROM file |
| `EMULATION_SPEED` | `1` | Speed multiplier (0=max, 1=normal) |
| `HEADLESS` | `false` | Run without display window |
| `AGENT_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## How It Works

1. **Game Loop**: Reads game state from memory every ~0.5 seconds
2. **State Reading**: Extracts position, party Pokemon, badges, battle state
3. **Claude Decision**: Sends state to Claude, which returns a tool call (press button, move, wait)
4. **Action Execution**: Executes the action via PyBoy input events
5. **Repeat**: Loop continues until interrupted

## Project Structure

```
Project_RED/
├── docs/                    # Architecture documentation
├── roms/                    # ROM files (gitignored)
├── src/
│   ├── __init__.py
│   ├── main.py             # Entry point, game loop
│   ├── config.py           # Configuration management
│   ├── logging_config.py   # Structured logging
│   ├── emulator/
│   │   ├── interface.py    # PyBoy wrapper
│   │   └── state_reader.py # Memory reading
│   └── agent/
│       └── simple_agent.py # Claude agent
├── pyproject.toml          # Dependencies
├── .env.example            # Environment template
└── README.md
```

## Observing the Agent

When running with a visible window (`HEADLESS=false`):
- Watch the Game Boy screen as Claude plays
- Console logs show each action and reasoning
- Press Ctrl+C to stop gracefully

## Limitations (MVP)

This is a minimal viable product. Current limitations:
- Single "unified" agent (no specialized battle/navigation agents)
- No UI dashboard (console only)
- No knowledge base (limited Pokemon/map data)
- May get stuck in complex menus

## Next Steps

See `docs/pokemon_red_agent_technical_design.md` for the full architecture including:
- Multi-agent system (Orchestrator, Navigation, Battle, Menu)
- React dashboard with real-time streaming
- Knowledge bases (Pokemon data, maps, trainers)
- WebSocket API

## License

This project is for educational purposes. You must provide your own legally obtained ROM file.
