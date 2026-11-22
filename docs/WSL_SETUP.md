# WSL2 Setup — Verified Installation

Actual, working setup for this project on this machine (installed and verified 2026-11-21).

| Host | |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| WSL | WSL2, Ubuntu 26.04.1 LTS |
| Resources | 4 vCPU, 3.3 GiB RAM (WSL), 949 GiB free |
| Linux user | `nouman_mukhtar` (passwordless sudo) |
| Project path | `/mnt/c/Users/Nouman Mukhtar/.local/share/opencode/worktree/e1123e/clever-garden` |

---

## Installed components

| Component | Version | Location | Activated by |
|---|---|---|---|
| Icarus Verilog | 12.0 | `/usr/bin` | apt |
| GTKWave | 3.3.126 | `/usr/bin` | apt (WSLg GUI) |
| hexdump | util-linux 2.41.3 | `/usr/bin` | apt |
| Python (system) | 3.14.4 | `/usr/bin` | apt |
| uv | 0.13.9 | `~/.local/bin/uv` | `~/.bashrc` PATH |
| CPython (project) | 3.13.18 | `~/.local/share/uv/python/...` | uv-managed |
| Project venv | cocotb 2.0.1, pytest 9.1.1 | `~/.venvs/caid-soc` | `UV_PROJECT_ENVIRONMENT` |
| RISC-V GNU toolchain | 2026.10.29, GCC 16.1.0 | `/opt/riscv` | `/etc/profile.d/riscv-toolchain.sh` |
| OSS CAD Suite | 2026-11-20 | `/opt/oss-cad-suite` | `/etc/profile.d/oss-cad-suite.sh` |
| — Yosys | 0.71+59 | | |
| — nextpnr-himbaechel | 0.11.1-119 | | |
| — nextpnr-ecp5 / ecppack / gowin_pack | bundled | | |
| — Verilator | 5.055 | | |
| — openFPGALoader | 1.2.0 | | |
| Verible | v0.0-4302 | `/opt/verible` | `/etc/profile.d/verible.sh` |
| KLayout | 0.30.13 (Qt5, embedded Ruby 3.3) | `/usr/bin/klayout` | apt (official Ubuntu 26 .deb) |
| KLayout Python module | 0.30.13 (`klayout.db`, `pya`) | `~/.venvs/klayout` | `klayout-python` wrapper |
| CIEL | 3.2.0 | `~/.local/bin/ciel` | `uv tool` |
| IHP SG13G2 PDK | `3b5a704b`, 787 MB | `~/.ciel/ihp-sg13g2` | `ciel enable` |
| LibreLane devshell | 3.0.17 (1.4 GB) | `/opt/librelane/librelane-devshell-x86_64.AppImage` | `librelane-shell` |

The RISC-V binaries are also symlinked into `/usr/local/bin` as
`riscv64-unknown-elf-{gcc,as,objcopy,objdump,...}` (the names `build.sh` expects).

---

## Verified results

| Check | Result |
|---|---|
| Functional-unit tests | 8/8 PASS |
| RV32I ISA tests (37 instructions) | 7/7 PASS |
| Wishbone tests | 2/2 PASS |
| Assembled + GCC hex programs | 6/6 PASS |
| **Total cocotb** | **23/23 PASS** |
| `make build-asm` / `build-gcc` / `rom.mem` | OK |
| Yosys `synth` on `riscv_top` | OK (exit 0) |
| Yosys `synth_gowin` on `fpga_top` | OK (exit 0) |
| Verible lint | runs (style findings only) |
| CIEL → PDK install | OK (`ciel output` = `3b5a704b`) |
| KLayout GDS write/read round trip | OK |
| KLayout loading `sg13g2.lyt` | OK (`tech-load-ok`) |
| KLayout Python (`klayout.db` / `pya`) | OK (GDS round trip via `klayout-python`) |

---

## ASIC stack (installed, flow not run)

The ASIC tools are installed but the LibreLane flow was intentionally **not
executed**, because LibreLane specifies 8 GiB RAM minimum (16 GiB recommended)
and this WSL has 3.3 GiB.

Installed:

| Item | Detail |
|---|---|
| LibreLane devshell | `/opt/librelane/librelane-devshell-x86_64.AppImage` (3.0.17), SHA-256 `c8ef5ae2…b36833c` verified |
| CIEL | `~/.local/bin/ciel` (3.2.0, uv tool) |
| PDK root | `~/.ciel` (787 MB) |
| Active PDK | `ihp-sg13g2` → `3b5a704ba6738aa686b08706187830e6284d2a10` |
| KLayout | 0.30.13 at `/usr/bin/klayout`; PDK tech in `~/.ciel/ihp-sg13g2/libs.tech/klayout/tech` (`sg13g2.lyt`) |

```bash
# confirm PDK
ciel ls --pdk-family ihp-sg13g2
ciel output --pdk-family ihp-sg13g2

# enter the LibreLane environment (first run downloads its Nix closure)
librelane-shell

# inside the devshell, from the project root:
librelane --version
make librelane PDK_ROOT=$HOME/.ciel
```

If a full run is attempted, raise WSL memory first (see
`C:\Users\<you>\.wslconfig`: `memory=6GB`, `swap=8GB`) and restart WSL, or run on
a machine with ≥16 GiB.

---

## Daily use

Open WSL as the normal user:

```bash
wsl -d Ubuntu
cd "/mnt/c/Users/Nouman Mukhtar/.local/share/opencode/worktree/e1123e/clever-garden"
```

Run the full suite:

```bash
cd tests/cocotb
WAVES=1 uv run run_tests.py
```

Run the lockstep differential demo (all 37 instructions, RTL vs. Python model):

```bash
cd tests/demo
uv run python run_demo.py
```

Build programs / ROM:

```bash
make build-asm
make build-gcc
make rom.mem
```

View waveforms (WSLg opens the GUI on Windows):

```bash
gtkwave tests/cocotb/waves/riscv_top.fst
```

View a GDSII layout (WSLg opens the GUI on Windows):

```bash
klayout final/asic_top.gds
```

Script GDSII from Python:

```bash
klayout-python script.py
```

```python
import klayout.db as db          # standalone API: Layout, Region, Box, ...
ly = db.Layout()
ly.read("final/asic_top.gds")
print(ly.cells())
```

FPGA:

```bash
make fpga-tangnano9k     # or: make fpga-icesuger
```

> Non-login shells do not read `/etc/profile.d`. Use `bash -l` (or `wsl -d Ubuntu`
> normally) so `/opt/riscv/bin`, `/opt/oss-cad-suite/bin`, and `/opt/verible/bin`
> are on `PATH`. The uv venv is selected by `UV_PROJECT_ENVIRONMENT` in `~/.bashrc`.

---

## Caveats and fixes applied

1. **`WAVES=1` is required.** `run_tests.py` always copies `sim_build/<top>.fst`
   after each test, but Icarus only generates it when waves are enabled at build
   time. Without `WAVES=1` the tests pass and then the script raises
   `FileNotFoundError`. `run_tests.sh` sets it; replicate that.

2. **CRLF line endings.** Windows checkout (`core.autocrlf=true`) gave CRLF to the
   `Makefile`, `*.sh`, `*.ys`, and `*.filelist`. Linux `bash`/`make` reject that.
   They were normalized to LF and `bash -n` verified. If they are ever re-checked
   out from Windows, re-run:
   ```bash
   find . -type f \( -name '*.sh' -o -name 'Makefile' -o -name '*.ys' -o -name '*.filelist' \) -not -path './.git/*' -print0 | xargs -0 sed -i 's/\r$//'
   ```

3. **`/tmp` does not survive a WSL restart.** Interrupted downloads cached in
   `/tmp` are lost when WSL shuts down.

4. **Verible rule syntax changed.** The repo's `.rules.verible_lint` / VS Code
   config use `line-length=180`; Verible 0.0-4302 requires
   `line-length=length:180`. Override on the command line:
   ```bash
   verible-verilog-lint --rules_config_search --rules=-always-comb,line-length=length:180 $(cat verible.filelist)
   ```

5. **Yosys FPGA script has a hard-coded path.** `fpga/*/yosys.ys` references
   `/home/blockzilla/ic-design/...` for `IMEM_HEX_PATH`; edit it to your path
   before `make fpga-*`. `.vscode/settings.json` has the same stale prefix for
   Verible.

6. **Normal warnings (not failures):**
   - `$readmemh: Not enough words ... [0:511]` — the memories are 512 words, the
     images are shorter.
   - `LOAD segment with RWX permissions` — the project's linker script uses one
     RWX segment.
   - Yosys tri-state warning on `mux3.v` — limited tri-state support, harmless here.
   - `fpga_top.v: Port 3 (gpio_data) ... expects 8 bits, got 7` — width padding.

7. **LibreLane flow not run.** The devshell, CIEL, and IHP SG13G2 PDK are
   installed, but the ASIC flow requires 8 GiB RAM minimum (16 GiB recommended);
   this WSL has 3.3 GiB. Raising WSL memory to ~6 GB may allow a partial run.
   See `docs/TOOLCHAIN.md` §5.

8. **PATH ordering (important).** OSS CAD Suite's `bin` is **appended** to `PATH`,
   not prepended, so the stable distro `iverilog` 12 / `vvp` / `gtkwave` are used
   for cocotb. The suite's Icarus 14 (devel) embeds its own `tabbypy3` interpreter
   and makes cocotb log `Unexpected sys.executable` on every test (tests still
   pass, but the log is noisy). The suite's `py3bin` is removed from `PATH`
   entirely, and `VIRTUAL_ENV` is unset, so the project's uv-managed Python is
   never replaced. Yosys, nextpnr, gowin_pack, ecppack, openFPGALoader, and
   Verilator still resolve from the suite because the distro has no equivalents.

9. **KLayout Python module lives in its own venv.** `uv tool install klayout`
   fails ("No executables are provided by package `klayout`"), and installing it
   into the project venv would be pruned by the next `uv sync`. It therefore
   lives in `~/.venvs/klayout` with a `klayout-python` wrapper. That venv's
   `bin` is deliberately **not** on `PATH`, so `/usr/bin/klayout` (the GUI app)
   still wins. Use `import klayout.db as db` for standalone scripting;
   `pya` imports but `pya.Application` only exists inside the running KLayout
   application.

10. **Verible rule syntax.** Verible 0.0-4302 expects
    `line-length=length:180`; the repository config (`.rules.verible_lint` and
    `.vscode/settings.json`) has been updated to that spelling, and the lint
    run is clean:

    ```bash
    verible-verilog-lint --rules_config_search \
      --rules=-always-comb,line-length=length:180 $(cat verible.filelist)
    ```

    The Verible binaries live in `/opt/verible/bin` (referenced by the VS Code
    settings, so use the Remote-WSL extension).

---

## Reinstall / repair commands

```bash
# base
sudo apt update && sudo apt install -y build-essential git make curl wget unzip \
  iverilog gtkwave bsdextrautils python3 python3-venv jq

# uv + python + deps
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13
UV_PROJECT_ENVIRONMENT=$HOME/.venvs/caid-soc uv sync

# RISC-V toolchain
# https://github.com/riscv-collab/riscv-gnu-toolchain/releases -> riscv64-elf-ubuntu-24.04-gcc.tar.xz
# extract to /opt/riscv

# FPGA/ASIC tools
# https://github.com/YosysHQ/oss-cad-suite-build/releases -> oss-cad-suite-linux-x64-*.tgz
# extract to /opt/oss-cad-suite

# Verible
# https://github.com/chipsalliance/verible/releases -> *-linux-static-x86_64.tar.gz
# extract to /opt/verible
```
