# RV32I Verification Report

**Design:** `caid-soc` — single-cycle RV32I core (`rtl/riscv/`) with a Wishbone
bus (`rtl/wishbone/`), FPGA top (`rtl/fpga/`) and ASIC top (`rtl/asic/`).

**Scope:** all 37 implemented RV32I instructions.

**Date:** 2026-11-22 · **Simulator:** Icarus Verilog 12.0 · **Framework:** cocotb 2.0.1 / Python 3.13.18

---

## 1. Result summary

| Check | Scope | Result |
|---|---|---|
| Directed regression (repo suite, clean tree) | 23 cocotb tests | **23 PASS / 0 FAIL** |
| Lockstep differential verification (new) | 57 executed instructions | **RTL ≡ reference model** |
| Program checksum | `M[0x40]` | `0x00000110` ✓ |
| Yosys synthesis | `riscv_top`, `fpga_top` | exit 0 |
| **Bugs found** | — | **2 — one in the RTL (`sra`/`srai`), one in the test tooling (assembler)** |

---

## 2. Verification method

Two independent methods are used, so a bug has to fool both to survive.

### 2.1 Directed regression (existing suite)

`tests/cocotb/run_tests.py` runs the repo's own tests: 8 functional-unit tests,
7 ISA group tests, 2 Wishbone tests, and 6 whole-program tests (assembled `.s`
and GCC-compiled `.c` programs checked against the `tinyrv` reference model).

```
WISHBONE_TEST=1 ASM_TEST=1 GCC_TEST=1 WAVES=1 uv run run_tests.py
```

| Suite | Tests | Result |
|---|---|---|
| `test_functional_units` (PC, ALU, ALU ctrl, imm gen, branch, data mem, inst mem, regfile) | 8 | PASS |
| `test_isa_rv32i` (imm / I-type / R-type / store / load / jump / branch) | 7 | PASS |
| `test_wishbone_slaves` | 1 | PASS |
| `test_wishbone_mem` | 1 | PASS |
| `test_hex_file` (asm_fibonacci, gcc_fibonacci, gcc_mem_test) | 3 | PASS |
| `test_wb_hex_file` (asm_wb_mem_test, gcc_wb_fpga_test, gcc_wb_gcc_test) | 3 | PASS |
| **Total** | **23** | **23 PASS** |

### 2.2 Lockstep differential verification (new — `tests/demo/`)

A program that uses **all 37 instructions** is assembled with the real
toolchain, loaded into the RTL core, and executed while a **Python RV32I
reference model** (`tests/demo/rv32i_ref.py`) executes the same instruction
stream in parallel.

After *every* instruction the test compares:

* the program counter
* the fetched instruction word
* all 31 writable registers
* every byte written to data memory

The reference model was written directly from the RTL sources
(`rtl/riscv/*.v`), including its quirks: `x0` hard-wired to zero
(`register_file.v`), byte-addressed little-endian data memory
(`data_memory.v`), and branch/jump targets forced to even addresses
(`riscv_top.v`).

```bash
cd tests/demo && uv run python run_demo.py
```

---

## 3. Instruction coverage — all 37

Each instruction is proven twice: by the repo's directed test and by the
lockstep differential run (step numbers refer to the trace in §4).

| # | Instruction | Directed test (`test_isa_rv32i.py`) | Demo step |
|---|---|---|---|
| 1 | `lui` | `test_imm_inst` | 4 |
| 2 | `auipc` | `test_imm_inst` | 5 |
| 3 | `addi` | `test_alu_imm_inst` | 1, 2, 3, 6 |
| 4 | `slti` | `test_alu_imm_inst` | 7 |
| 5 | `sltiu` | `test_alu_imm_inst` | 8 |
| 6 | `xori` | `test_alu_imm_inst` | 9 |
| 7 | `ori` | `test_alu_imm_inst` | 10 |
| 8 | `andi` | `test_alu_imm_inst` | 11 |
| 9 | `slli` | `test_alu_imm_inst` | 12 |
| 10 | `srli` | `test_alu_imm_inst` | 13 |
| 11 | `srai` | `test_alu_imm_inst` (explicit encoding) | 14 |
| 12 | `add` | `test_alu_inst` | 15 |
| 13 | `sub` | `test_alu_inst` | 16 |
| 14 | `sll` | `test_alu_inst` | 17 |
| 15 | `slt` | `test_alu_inst` | 18 |
| 16 | `sltu` | `test_alu_inst` | 19 |
| 17 | `xor` | `test_alu_inst` | 20 |
| 18 | `srl` | `test_alu_inst` | 21 |
| 19 | `sra` | `test_alu_inst` (+ new negative-operand check) | 22 |
| 20 | `or` | `test_alu_inst` | 23 |
| 21 | `and` | `test_alu_inst` | 24 |
| 22 | `sw` | `test_store_inst` | 25 |
| 23 | `lw` | `test_load_inst` | 26, 34 |
| 24 | `lb` | `test_load_inst` | 27, 35 |
| 25 | `lbu` | `test_load_inst` | 28, 36 |
| 26 | `lh` | `test_load_inst` | 29, 37 |
| 27 | `lhu` | `test_load_inst` | 30, 38 |
| 28 | `sh` | `test_store_inst` | 32 |
| 29 | `sb` | `test_store_inst` | 33 |
| 30 | `jal` | `test_jump_inst` | 50 |
| 31 | `jalr` | `test_jump_inst` | 53 |
| 32 | `beq` | `test_branch_inst` | 39 (not taken), 49 (taken) |
| 33 | `bne` | `test_branch_inst` | 41 (not taken), 48 (taken) |
| 34 | `blt` | `test_branch_inst` | 43 (taken) |
| 35 | `bge` | `test_branch_inst` | 44 (taken) |
| 36 | `bltu` | `test_branch_inst` | 45 (not taken) |
| 37 | `bgeu` | `test_branch_inst` | 47 (taken) |

Branches are additionally exercised in *both* directions by the directed test
(`assert_branch(..., taken=True/False)`), so signed vs. unsigned comparison
(`blt`/`bge` vs. `bltu`/`bgeu`) is checked with positive **and** negative
operands.

---

## 4. Execution trace (lockstep differential run)

`tests/demo/rv32i_demo.s`, 57 executed instructions. `WORD` is the encoding
fetched by the core; `RESULT` is the value confirmed on the RTL *and* in the
reference model.

```
  #          PC        WORD  INSTRUCTION                RESULT
  1  0x00000000  0x00a00093  addi x1, x0, 10            x1 = 0x0000000a
  2  0x00000004  0xfec00113  addi x2, x0, -20           x2 = 0xffffffec
  3  0x00000008  0x00700193  addi x3, x0, 7             x3 = 0x00000007
  4  0x0000000c  0x12345237  lui x4, 0x12345            x4 = 0x12345000
  5  0x00000010  0x00000297  auipc x5, 0x0              x5 = 0x00000010
  6  0x00000014  0x00708313  addi x6, x1, 7             x6 = 0x00000011
  7  0x00000018  0x00a12393  slti x7, x2, 10            x7 = 0x00000001
  8  0x0000001c  0x00a13413  sltiu x8, x2, 10           x8 = 0x00000000
  9  0x00000020  0x00f0c493  xori x9, x1, 15            x9 = 0x00000005
 10  0x00000024  0x0300e513  ori x10, x1, 48           x10 = 0x0000003a
 11  0x00000028  0x0030f593  andi x11, x1, 3           x11 = 0x00000002
 12  0x0000002c  0x00309613  slli x12, x1, 3           x12 = 0x00000050
 13  0x00000030  0x00115693  srli x13, x2, 1            x13 = 0x7ffffff6
 14  0x00000034  0x40115713  srai x14, x2, 1            x14 = 0xfffffff6
 15  0x00000038  0x003087b3  add x15, x1, x3            x15 = 0x00000011
 16  0x0000003c  0x40118833  sub x16, x3, x1            x16 = 0xfffffffd
 17  0x00000040  0x003098b3  sll x17, x1, x3            x17 = 0x00000500
 18  0x00000044  0x00112933  slt x18, x2, x1            x18 = 0x00000001
 19  0x00000048  0x001139b3  sltu x19, x2, x1           x19 = 0x00000000
 20  0x0000004c  0x0030ca33  xor x20, x1, x3            x20 = 0x0000000d
 21  0x00000050  0x00315ab3  srl x21, x2, x3            x21 = 0x01ffffff
 22  0x00000054  0x40315b33  sra x22, x2, x3            x22 = 0xffffffff
 23  0x00000058  0x0030ebb3  or x23, x1, x3             x23 = 0x0000000f
 24  0x0000005c  0x0030fc33  and x24, x1, x3            x24 = 0x00000002
 25  0x00000060  0x00102023  sw x1, 0(x0)               M[0x0] = 0x0000000a
 26  0x00000064  0x00002c83  lw x25, 0(x0)              x25 = 0x0000000a
 27  0x00000068  0x00000d03  lb x26, 0(x0)              x26 = 0x0000000a
 28  0x0000006c  0x00004d83  lbu x27, 0(x0)             x27 = 0x0000000a
 29  0x00000070  0x00001e03  lh x28, 0(x0)              x28 = 0x0000000a
 30  0x00000074  0x00005e83  lhu x29, 0(x0)             x29 = 0x0000000a
 31  0x00000078  0x00202223  sw x2, 4(x0)               M[0x4] = 0xffffffec
 32  0x0000007c  0x00201423  sh x2, 8(x0)               M[0x8] = 0xffffffec
 33  0x00000080  0x00200623  sb x2, 12(x0)              M[0xc] = 0xffffffec
 34  0x00000084  0x00402c83  lw x25, 4(x0)              x25 = 0xffffffec
 35  0x00000088  0x00400d03  lb x26, 4(x0)              x26 = 0xffffffec
 36  0x0000008c  0x00404d83  lbu x27, 4(x0)             x27 = 0x000000ec
 37  0x00000090  0x00401e03  lh x28, 4(x0)              x28 = 0xffffffec
 38  0x00000094  0x00405e83  lhu x29, 4(x0)             x29 = 0x0000ffec
 39  0x00000098  0x00208463  beq x1, x2, 0x000000a0     not taken, pc -> 0x0000009c
 40  0x0000009c  0x01100f13  addi x30, x0, 17           x30 = 0x00000011
 41  0x000000a0  0x00109463  bne x1, x1, 0x000000a8     not taken, pc -> 0x000000a4
 42  0x000000a4  0x02200f13  addi x30, x0, 34           x30 = 0x00000022
 43  0x000000a8  0x00114463  blt x2, x1, 0x000000b0     taken, pc -> 0x000000b0
 44  0x000000b0  0x0020d463  bge x1, x2, 0x000000b8     taken, pc -> 0x000000b8
 45  0x000000b8  0x00116463  bltu x2, x1, 0x000000c0    not taken, pc -> 0x000000bc
 46  0x000000bc  0x05500f13  addi x30, x0, 85           x30 = 0x00000055
 47  0x000000c0  0x00117463  bgeu x2, x1, 0x000000c8    taken, pc -> 0x000000c8
 48  0x000000c8  0x00209463  bne x1, x2, 0x000000d0     taken, pc -> 0x000000d0
 49  0x000000d0  0x00108463  beq x1, x1, 0x000000d8     taken, pc -> 0x000000d8
 50  0x000000d8  0x00800e6f  jal x28, 0x000000e0        x28 = 0x000000dc, pc -> 0x000000e0
 51  0x000000e0  0x00000d17  auipc x26, 0x0             x26 = 0x000000e0
 52  0x000000e4  0x010d0d13  addi x26, x26, 16          x26 = 0x000000f0
 53  0x000000e8  0x000d0de7  jalr x27, 0(x26)           x27 = 0x000000ec, pc -> 0x000000f0
 54  0x000000f0  0x0bb00e93  addi x29, x0, 187          x29 = 0x000000bb
 55  0x000000f4  0x01df0f33  add x30, x30, x29          x30 = 0x00000110
 56  0x000000f8  0x05e02023  sw x30, 64(x0)              M[0x40] = 0x00000110
 57  0x000000fc  0x0000006f  jal x0, 0x000000fc         no link write (x0), pc -> 0x000000fc
```

Final register file (after the program halts):

```
x1  = 0x0000000a    x9  = 0x00000005    x17 = 0x00000500    x25 = 0xffffffec
x2  = 0xffffffec    x10 = 0x0000003a    x18 = 0x00000001    x26 = 0xffffffec
x3  = 0x00000007    x11 = 0x00000002    x19 = 0x00000000    x27 = 0x000000ec
x4  = 0x12345000    x12 = 0x00000050    x20 = 0x0000000d    x28 = 0x000000dc
x5  = 0x00000010    x13 = 0x7ffffff6    x21 = 0x01ffffff    x29 = 0x000000bb
x6  = 0x00000011    x14 = 0xfffffff6    x22 = 0xffffffff    x30 = 0x00000110
x7  = 0x00000001    x15 = 0x00000011    x23 = 0x0000000f    x31 = 0x00000000
x8  = 0x00000000    x16 = 0xfffffffd    x24 = 0x00000002
```

Checksum: `M[0x40] = 0x00000110` (= `0x55 + 0xBB`), matching the reference model.

---

## 5. Bug found and fixed: `sra` / `srai` did not sign-extend

**Severity:** functional — `sra`/`srai` are not RV32I compliant.

**Root cause** — `rtl/riscv/alu.v`:

```verilog
`ALU_OP_SRA: result <= A >>> B;      // BUG: A is unsigned
```

In Verilog the `>>>` operator is only an *arithmetic* shift when its left
operand is **signed**. `A` is declared `input [31:0] A` (unsigned), so
`A >>> B` behaves exactly like `A >> B` — a logical shift. The decode side was
correct the whole time (`alu_control.v` selects `ALU_OP_SRA` for
`funct7 = 0100000`), so the fault was invisible in the control path.

**Impact:** any negative operand produced the wrong result, e.g.
`srai x14, x2, 1` with `x2 = -20` returned `0x7FFFFFF6` instead of
`0xFFFFFFF6`.

**Why the existing tests missed it:** `test_isa_rv32i.py` only shifted a
*positive* value (`srai x4, x5, 5` with `x5 = 25` → `0`, and `sra x4, x5, x6`
with `x5 = 24`, `x6 = 3` → `3`). Logical and arithmetic shifts agree on
non-negative operands, so the defect could not surface.

**Fix:**

```diff
-            `ALU_OP_SRA: result <= A >>> B;
+            `ALU_OP_SRA: result <= $signed(A) >>> B;
```

**Regression coverage added** to `tests/cocotb/test_isa_rv32i.py` (negative
operand, logical and arithmetic variants):

```python
await exec_imm(dut, "addi x6, x0, -16")
await exec_imm(dut, "srai x4, x6, 2")
assert_reg(dut, 4, -4, "srai must be an arithmetic shift")
await exec_imm(dut, "srli x4, x6, 2")
assert_reg(dut, 4, 0x3FFF_FFFC, "srli must be a logical shift")
```

The differential demo additionally pins `srli` vs `srai` and `srl` vs `sra` on a
negative operand in the same program.

---

## 6. Second finding: `riscv_assembler` mis-encodes `srai`

**Severity:** test infrastructure — it silently removed all `srai` coverage.

`riscv_assembler` 1.2.1 (the Python assembler used by
`tests/cocotb/test_isa_rv32i.py`) encodes the I-type arithmetic shift with the
wrong `funct7`:

```
srai x4, x6, 2   -> 0x00235213   funct7 = 0x00   <-- actually an SRli
expected          0x40235213   funct7 = 0x20
srli x4, x6, 2   -> not supported at all ("Bad Instruction Provided: srli!")
sra  x4, x6, x5  -> 0x40535233   funct7 = 0x20   <-- R-type is encoded correctly
sll  x4, x6, x5  -> 0x00531233   funct7 = 0x00   <-- correct
srl  x4, x6, x5  -> 0x00535233   funct7 = 0x00   <-- correct
```

**Consequence:** the existing test line

```python
await exec_imm(dut, "srai x4, x5, 5")     # <- was actually executing an srli
```

never tested `srai` at all. Together with the RTL defect in §5 this produced
**two independent bugs that cancelled out**: the ALU turned `srai` into a
logical shift, and the assembler turned `srai` into `srli` — a test that
appears to cover `srai` but asserts nothing about arithmetic shifting.

**Fix:** use explicit encodings in the tests (the repo already does this for
`srli`):

```python
await exec_imm(dut, 0x40545213)  # srai x4, x5, 5
await exec_imm(dut, 0x40235213)  # srai x4, x6, 2
await exec_imm(dut, 0x00235213)  # srli x4, x6, 2
```

The GNU assembler (`riscv64-unknown-elf-as`) is unaffected and encodes `srai`
correctly — which is why the demo program in `tests/demo/` exercises the real
`srai` encoding and caught the RTL bug.

**Note for future work:** `riscv-assembler` is pinned as `>=1.2.1` in
`pyproject.toml`. Until upstream fixes it, any test that relies on the
`srai` mnemonic must use a literal encoding.

---

## 7. Reproduction

```bash
cd tests/demo && uv run python run_demo.py     # lockstep differential run
cd tests/cocotb && WAVES=1 uv run run_tests.py  # directed regression
```

Artifacts:

| Artifact | Location |
|---|---|
| Assembled demo program | `tests/demo/build/rv32i_demo.{elf,bin,mem,lst}` |
| Demo waveform | `tests/demo/sim_build/riscv_top.fst` |
| Regression waveforms | `tests/cocotb/waves/*.fst` |
| ROM image for FPGA/ASIC | `rom.mem` (from `make rom.mem`) |
