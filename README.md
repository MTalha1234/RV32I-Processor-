# RV32I Processor

A single-cycle **RV32I** processor with a Wishbone bus, FPGA and ASIC targets.

* RTL: `rtl/riscv/` (core), `rtl/wishbone/` (bus + slaves), `rtl/fpga/`, `rtl/asic/`
* Verification: cocotb testbenches + a lockstep differential harness against an independent Python reference model
* Tooling: Icarus Verilog, cocotb, RISC-V GNU toolchain, Yosys/nextpnr, LibreLane + IHP SG13G2

---

## Features

| | |
|---|---|
| **ISA** | 37 RV32I instructions — `lui`, `auipc`, the 9 I-type ALU ops, the 10 R-type ALU ops, 5 loads, 3 stores, `jal`, `jalr` and all 6 branches |
| **Bus** | Wishbone master with memory and GPIO slaves |
| **Memory** | Byte-addressed little-endian data memory, word-addressed instruction memory (loads ROM from a `.mem` image) |
| **FPGA** | ECP5 25k (`soc.bit`) and Tang Nano 9K (`soc.fs`) — both place & route and meet timing |
| **ASIC** | IHP SG13G2 via LibreLane (PDK + devshell installed, flow ready to run) |

## Verification

| Check | Scope | Result |
|---|---|---|
| Cocotb regression | 23 tests (functional units, ISA, Wishbone, whole programs) | **23 PASS / 0 FAIL** |
| Lockstep differential run | 57 executed instructions, RTL vs. Python reference model | **RTL ≡ model** |
| Encoder cross-check | all 37 instructions vs. GNU `as` | **37/37 match** |
| Verible lint | whole RTL | **0 findings** |
| Yosys synthesis | `riscv_top`, `fpga_top` (`synth_gowin`) | exit 0 |
| Place & route | ECP5: 64.24 MHz (PASS @ 25 MHz) · Tang Nano 9K: 24.71 MHz (PASS @ 12 MHz) | pass |

The differential harness executes a program that uses **all 37 instructions** and,
after every instruction, compares the program counter, the fetched word, all 31
registers and every written memory byte against a Python RV32I reference model
written from the RTL sources.

It has already earned its keep — two real bugs were found:

1. **`sra`/`srai` did not sign-extend.** `rtl/riscv/alu.v` used `A >>> B` on an
   *unsigned* operand, so Verilog treated it as a logical shift. Fixed with
   `$signed(A) >>> B`.
2. **`riscv_assembler` mis-encoded `srai`** as an `srli` and did not support
   `srli` at all, so the original test never exercised `srai` — the two defects
   masked each other. The dependency was replaced by a small local encoder that
   is cross-checked against the GNU assembler.

Full report: [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Repository layout

```
rtl/
  riscv/        core: alu, control, imm/branch units, register file, memories, pc
  wishbone/     bus master, address/data decoders, memory + GPIO slaves
  fpga/         fpga_top, reset generator
  asic/         asic_top
tests/
  cocotb/       cocotb testbenches + local RV32I encoder (tests/cocotb/asm.py)
  demo/         lockstep differential harness (program, reference model, runner)
  assembly/     hand-written assembly programs
  gcc/          C test programs
fpga/           ECP5 and Tang Nano 9K flows (yosys + nextpnr + packer)
librelane/      ASIC flow configuration
docs/           toolchain reference, WSL2 setup, verification report
```

## Quick start

Full toolchain setup (WSL2 / Ubuntu): [`docs/WSL_SETUP.md`](docs/WSL_SETUP.md)
Toolchain overview: [`docs/TOOLCHAIN.md`](docs/TOOLCHAIN.md)

```bash
uv sync                                     # cocotb, pytest, tinyrv
make build-asm && make build-gcc           # test programs (needs the RISC-V toolchain)
cd tests/cocotb && WAVES=1 uv run run_tests.py    # 23-test regression
cd tests/demo  && uv run python run_demo.py      # lockstep differential run
```

FPGA:

```bash
make fpga-icesuger      # -> fpga/icesuger/soc.bit
make fpga-tangnano9k   # -> fpga/tangnano9k/soc.fs
```

ASIC:

```bash
librelane-shell        # LibreLane devshell (PDK at ~/.ciel)
make librelane PDK_ROOT=$HOME/.ciel
```

## License

See the upstream project this work is based on.
