[中文](README.md) | English

# Automated Test Tool

A Tkinter desktop app that controls an ITECH IT8811 electronic load, collects voltage from a Keithley DMM6500 and current from a Keysight 34461A, and exports measurements to CSV.

## Install and run

- Download the Windows executable from [GitHub Releases](https://github.com/Sandman6z/smartInstrument/releases).
- To run from source, use a Python installation with Tkinter available. CI checks a regular installation on Windows with Python 3.11.
- Either way, install a VISA backend on the instrument PC, such as [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) or Keysight IO Libraries. The Windows executable does not include these drivers.

Choose one method from the repository root:

```bash
# uv (uses the lockfile for runtime dependencies)
uv sync --locked --no-dev
uv run --locked --no-dev smart_instrument
```

```bash
# pip (preferably in an activated virtual environment)
python -m pip install .
python -m smart_instrument
```

## Use the app

1. On startup, the app scans VISA resources and tries to connect to recognized instruments, preferring LAN when an instrument has multiple connection options. If needed, select an address and connect manually.
2. Set the IT8811 resistance in the input box or with the slider (`100–7500 Ω`). Scrolling the mouse wheel over the slider changes the resistance by `100 Ω` at a time.
3. Connect all three instruments and set the load's **input** to `ON`. Trigger one measurement manually or start automatic collection, which sweeps down in `100 Ω` steps. Automatic collection only records when consecutive valid measurements differ by more than `20 W` in power, and can be stopped manually. Do not disconnect instruments while collecting.
4. Measurements fill the data table horizontally; use the horizontal scrollbar to see more. Export from File → Save Data to CSV. The file is written to the current working directory. Export before clearing the table or closing the app to retain the data.

## Build and release

Run from the repository root on Windows:

```bash
uv sync --locked --group dev
uv run --locked python scripts/build_nuitka.py  # dist_nuitka/SmartInstrument.exe
uv run --locked python scripts/build_exe.py     # dist/SmartInstrument.exe
```

Official releases use Nuitka. The first build may need to download C compiler tools. See [RELEASE.md](RELEASE.md) for the release process and the [architecture guide (Chinese)](docs/architecture.md) for module boundaries and maintenance checks.

## Troubleshooting

- **Instrument not found or connection failed:** Check the VISA backend, power, and USB or LAN connection. Default discovery and probe settings are in [`config.py`](src/smart_instrument/config.py).
- **Cannot collect data:** Check the connection status of all three instruments and the IT8811 input state.
- **Cannot export:** Check that the directory from which the app was launched is writable. Runtime logs are in `logs/` under that directory.

## License

[GNU GPL v3](LICENSE).
