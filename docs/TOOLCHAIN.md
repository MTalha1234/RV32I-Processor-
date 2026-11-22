# Toolchain Reference — RV32I SoC (`caid-soc`)

Reference list of everything needed to **build, execute, verify, and implement** this
RV32I processor. Nothing here is required all at once — pick the section that matches
what you want to do (simulate vs. FPGA vs. ASIC).

> **Verified working setup (WSL2, exact paths/versions/commands):** see
> [`docs/WSL_SETUP.md`](WSL_SETUP.md). This document is the generic reference.

---

## 0. What the design is

Single-cycle RV32I core plus a Wishbone bus and memories.

| Top module | File | Used for |
|---|---|---|
| `riscv_top` | `rtl/riscv/riscv_top.v` | Core-only simulation |
| `wb_top` | `rtl/wishbone/wb_top.v` | Core + Wishbone bus/slaves |
| `fpga_top` | `rtl/fpga/fpga_top.v` | FPGA bitstream |
| `asic_top` | `rtl/asic/asic_top.v` | LibreLane / ASIC flow |

### The 37 implemented instructions

| Group | Count | Instructions |
|---|---|---|
| Upper immediate | 2 | `lui`, `auipc` |
| I-type ALU | 9 | `addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`, `slli`, `srli`, `srai` |
| R-type ALU | 10 | `add`, `sub`, `sll`, `slt`, `sltu`, `xor`, `srl`, `sra`, `or`, `and` |
| Loads | 5 | `lb`, `lh`, `lw`, `lbu`, `lhu` |
| Stores | 3 | `sb`, `sh`, `sw` |
| Jumps | 2 | `jal`, `jalr` |
| Branches | 6 | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` |
| **Total** | **37** | |

Verified by `tests/cocotb/test_isa_rv32i.py`; full programs are verified by
`test_hex_file.py` / `test_wb_hex_file.py` against the `tinyrv` reference model.

---

## 1. Host environment (required for everything)

The repo's scripts are Linux/bash-oriented (`bash build.sh`, `hexdump`,
process substitution `<(...)`, `make`, `rm -rf`).

| Item | Why |
|---|---|
| **Linux** or **WSL2 (Ubuntu 22.04/24.04)** | All `build.sh`, `run_tests.sh`, and Makefile targets assume a POSIX shell |
| **Git** | Checkout / worktrees |
| **GNU Make** | `Makefile` targets (`build-asm`, `build-gcc`, `fpga-*`, `librelane`) |
| **Bash + coreutils/bsdextrautils** | `hexdump` is used to create `.mem` files |
| **Python 3.13** (pinned `>=3.13,<3.14`) | All test/automation code |
| **uv** | Dependency + venv manager (`uv.lock` is committed) |

> On native Windows the Python part runs, but the `.sh` build scripts and `hexdump`
> will fail. Use WSL2 (recommended) or Git Bash + a `hexdump` package.

Quick setup:

```bash
git clone <repo> && cd clever-garden
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync          # installs cocotb, cocotb-test, pytest, riscv-assembler, tinyrv
```

---

## 2. RTL simulation — "execute the 37 instructions"

This is the shortest path. The runner is hard-coded to **Icarus Verilog**
(`get_runner("icarus")` in `tests/cocotb/run_tests.py`).

| Software | Version used / needed | Role |
|---|---|---|
| **Icarus Verilog** (`iverilog`, `vvp`) | 12.x+ | Verilog simulator backend |
| **cocotb** | 2.0.1 | Python testbench / coroutine driver |
| **cocotb-test** | 0.2.6 | Pytest integration |
| **pytest** | 9.1.1 | Test runner |
| **RV32I encoder (local)** | `tests/cocotb/asm.py` | Encodes instruction strings in the ISA test; cross-checked against GNU `as` |
| **tinyrv** | 0.1.0 | Reference RV32I ISS used by the hex-file tests |
| **GTKWave** or **Surfer** | any recent | View `.fst` waveforms from `tests/cocotb/waves/` |
| *Optional:* **Verilator** | 5.x | Faster lint/alt simulation |
| *Optional:* **debugpy** | 1.8.21 | VS Code remote debug (already a dependency) |

Install on Ubuntu/WSL:

```bash
sudo apt update
sudo apt install iverilog gtkwave bsdextrautils
```

Run the core ISA tests (no RISC-V compiler needed):

```bash
cd tests/cocotb
uv run run_tests.py          # functional units + all 37 instructions
```

Run everything, including assembled/C programs and waveforms:

```bash
cd tests/assembly && bash build.sh
cd ../gcc        && bash build.sh
cd ../cocotb     && bash run_tests.sh    # sets WISHBONE_TEST/ASM_TEST/GCC_TEST + WAVES=1
```

---

## 3. Program build tools (assembly + C test programs)

Needed only for `make build-asm`, `make build-gcc`, `make rom.mem`, FPGA, and ASIC
(the ROM image is compiled from `tests/gcc/build/wb_fpga_test.mem`).

| Software | Role |
|---|---|
| **RISC-V GNU toolchain** (`riscv64-unknown-elf-*` or `riscv64-elf-*`) | `as`, `gcc`, `objcopy`, `objdump` targeting `rv32i` / `ilp32` |
| **hexdump** (`bsdextrautils`) | Converts `.bin` to word-per-line `.mem` |
| **linker script** | `tests/gcc/libs/link.ld` + `crt0.s` (no libc: `-nostdlib -ffreestanding`) |

`build.sh` tries both prefixes, so either naming works:

```bash
sudo apt install gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf
# or download the official prebuilt toolchain from:
# https://github.com/riscv-collab/riscv-gnu-toolchain/releases
```

Produces per program: `.elf`, `.bin`, `.dump`, `.mem`.

---

## 4. FPGA implementation

Targets in `fpga/`:

| Board | Toolchain | Tools |
|---|---|---|
| **Tang Nano 9K** (`GW1NR-LV9QN88PC6/I5`) | Gowin / Apicula | `yosys` (`synth_gowin`), `nextpnr-himbaechel`, `gowin_pack`, `openFPGALoader` |
| **iCEsuger / ECP5 25k** | Project Trellis | `yosys` (`synth_ecp5`), `nextpnr-ecp5`, `ecppack`, `openFPGALoader` |

Easiest install: **OSS CAD Suite** (bundles Yosys, nextpnr, gowin/ecp5 packers,
openFPGALoader, GTKWave):
<https://github.com/YosysHQ/oss-cad-suite-build/releases>

```bash
make build-gcc          # ROM image first
make fpga-tangnano9k    # or: make fpga-icesuger
```

**Caveats before running:**
- `fpga/tangnano9k/yosys.ys` hard-codes `IMEM_HEX_PATH="/home/blockzilla/..."` — edit it
  to your absolute path.
- You need the physical board + USB cable to actually program it (`make prog` inside
  the board folder).
- `.vscode/settings.json` also contains `/home/blockzilla/...` Verible paths — edit
  for your machine.

---

## 5. ASIC implementation (LibreLane + IHP SG13G2)

| Software | Role |
|---|---|
| **LibreLane** (v3 flow, `librelane` CLI) | RTL→GDSII flow orchestrator |
| **IHP SG13G2 PDK** (pinned commit) | Process design kit |
| **CIEL** | PDK downloader/manager (`PDK_ROOT=~/.ciel`) |
| Bundled by LibreLane: **OpenROAD, KLayout, Magic, Netgen, Yosys** | PnR, DRC/LVS, layout, STA |

```bash
# Install LibreLane per https://librelane.readthedocs.io (Nix recommended,
# or: uv tool install librelane)
pip install ciel
make clone-pdk          # ~several GB download
make librelane          # full flow -> final/ + librelane/runs/
```

Useful Makefile variants: `librelane-nodrc`, `librelane-to-pdn`,
`librelane-openroad` (GUI), `librelane-klayout` (layout).

Note the flow expects `rom.mem`, so `make build-gcc` must succeed first.

---

## 6. Editing, linting, waveforms

| Tool | Role |
|---|---|
| **Verible** (`verible-verilog-ls`, `-lint`, `-format`) | Verilog language server, lint, formatting |
| **VS Code** + Verilog/SystemVerilog + **Teros HDL** extensions | Editor (`.teros-hdl` config) |
| **GTKWave / Surfer** | `.fst` waveform inspection |
| **Excalidraw** | `docs/wishbone_signals.excalidraw` diagrams |

Repo configs already present: `verible.filelist`, `.rules.verible_lint`,
`.vscode/tasks.json` (Run tests / Build GCC / Build ASM).

```bash
verible-verilog-lint --rules_config_search --rules=-always-comb,line-length=180 \
  $(cat verible.filelist)
```

---

## 7. Minimum viable setup by goal

| Goal | Install |
|---|---|
| **Just run the 37-instruction tests** | Python 3.13 + `uv sync` + `iverilog` |
| **Compile & run C/asm programs** | above + RISC-V GNU toolchain + `hexdump` |
| **See waveforms** | above + GTKWave/Surfer |
| **Put it on a board** | above + OSS CAD Suite + Tang Nano 9K / ECP5 board |
| **Tape out / GDS** | above + LibreLane + CIEL + SG13G2 PDK |

---

## 8. Command quick reference

```bash
uv sync                       # Python deps
make build-asm                # assemble tests/assembly/src/*.s
make build-gcc                # compile tests/gcc/test_programs/*.c
make rom.mem                  # copy wb_fpga_test.mem -> rom.mem
make fpga-tangnano9k          # FPGA bitstream (Tang Nano 9K)
make fpga-icesuger            # FPGA bitstream (ECP5)
make librelane                # ASIC RTL->GDS
make clean                    # remove runs/build artifacts
```
