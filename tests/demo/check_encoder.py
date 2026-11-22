"""Cross-check the test-side RV32I encoder against the GNU assembler.

`tests/cocotb/asm.py` replaced the `riscv_assembler` package, which silently
mis-encoded `srai`. To make sure the replacement cannot drift, every one of
the 37 supported instructions is encoded twice: once by our encoder and once
by `riscv64-unknown-elf-as`. Any difference is a hard error.

Run directly (`python tests/demo/check_encoder.py`) or as part of the demo.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cocotb"))

from asm import encode  # noqa: E402

# (mnemonic, encoder input, assembler source)
# Branch/jump sources place a nop between the instruction and the label so the
# displacement is 8 bytes, matching the encoder's byte-offset semantics.
CHECKS = [
    ("lui", "lui x4, 0x12345", "lui x4, 0x12345"),
    ("auipc", "auipc x5, 0", "auipc x5, 0"),
    ("addi", "addi x6, x1, 7", "addi x6, x1, 7"),
    ("slti", "slti x7, x2, 10", "slti x7, x2, 10"),
    ("sltiu", "sltiu x8, x2, 10", "sltiu x8, x2, 10"),
    ("xori", "xori x9, x1, 0xF", "xori x9, x1, 0xF"),
    ("ori", "ori x10, x1, 0x30", "ori x10, x1, 0x30"),
    ("andi", "andi x11, x1, 3", "andi x11, x1, 3"),
    ("slli", "slli x12, x1, 3", "slli x12, x1, 3"),
    ("srli", "srli x13, x2, 1", "srli x13, x2, 1"),
    ("srai", "srai x14, x2, 1", "srai x14, x2, 1"),
    ("add", "add x15, x1, x3", "add x15, x1, x3"),
    ("sub", "sub x16, x3, x1", "sub x16, x3, x1"),
    ("sll", "sll x17, x1, x3", "sll x17, x1, x3"),
    ("slt", "slt x18, x2, x1", "slt x18, x2, x1"),
    ("sltu", "sltu x19, x2, x1", "sltu x19, x2, x1"),
    ("xor", "xor x20, x1, x3", "xor x20, x1, x3"),
    ("srl", "srl x21, x2, x3", "srl x21, x2, x3"),
    ("sra", "sra x22, x2, x3", "sra x22, x2, x3"),
    ("or", "or x23, x1, x3", "or x23, x1, x3"),
    ("and", "and x24, x1, x3", "and x24, x1, x3"),
    ("lb", "lb x26, 0(x0)", "lb x26, 0(x0)"),
    ("lh", "lh x28, 0(x0)", "lh x28, 0(x0)"),
    ("lw", "lw x25, 0(x0)", "lw x25, 0(x0)"),
    ("lbu", "lbu x27, 0(x0)", "lbu x27, 0(x0)"),
    ("lhu", "lhu x29, 0(x0)", "lhu x29, 0(x0)"),
    ("sb", "sb x2, 12(x0)", "sb x2, 12(x0)"),
    ("sh", "sh x2, 8(x0)", "sh x2, 8(x0)"),
    ("sw", "sw x1, 0(x0)", "sw x1, 0(x0)"),
    ("jal", "jal x28, 8", "jal x28, target\n    nop\ntarget:"),
    ("jalr", "jalr x27, 0(x26)", "jalr x27, 0(x26)"),
    ("beq", "beq x1, x2, 8", "beq x1, x2, target\n    nop\ntarget:"),
    ("bne", "bne x1, x2, 8", "bne x1, x2, target\n    nop\ntarget:"),
    ("blt", "blt x2, x1, 8", "blt x2, x1, target\n    nop\ntarget:"),
    ("bge", "bge x1, x2, 8", "bge x1, x2, target\n    nop\ntarget:"),
    ("bltu", "bltu x2, x1, 8", "bltu x2, x1, target\n    nop\ntarget:"),
    ("bgeu", "bgeu x2, x1, 8", "bgeu x2, x1, target\n    nop\ntarget:"),
]


def find_tool(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def assemble_words(source, workdir):
    """Assemble with GNU as and return the first instruction word."""
    assembler = find_tool("riscv64-unknown-elf-as", "riscv64-elf-as")
    objcopy = find_tool("riscv64-unknown-elf-objcopy", "riscv64-elf-objcopy")
    if not assembler or not objcopy:
        return None

    path = workdir / "probe.s"
    path.write_text(f"    .text\n    {source}\n")
    obj = workdir / "probe.o"
    binary = workdir / "probe.bin"

    subprocess.run(
        [assembler, "-march=rv32i", "-mabi=ilp32", "-o", str(obj), str(path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [objcopy, "-O", "binary", str(obj), str(binary)], check=True, capture_output=True
    )
    data = binary.read_bytes()
    return int.from_bytes(data[:4], "little")


def main():
    if not find_tool("riscv64-unknown-elf-as", "riscv64-elf-as"):
        print("GNU RISC-V assembler not found - skipping encoder cross-check")
        return 0

    failures = []
    print(f"{'MNEMONIC':<10} {'OURS':>10} {'GNU as':>10}  STATUS")
    print("-" * 46)
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        for mnemonic, ours, source in CHECKS:
            our_word = encode(ours)
            gas_word = assemble_words(source, workdir)
            ok = gas_word == our_word
            status = "ok" if ok else "MISMATCH"
            print(f"{mnemonic:<10} 0x{our_word:08x} 0x{gas_word:08x}  {status}")
            if not ok:
                failures.append((mnemonic, ours, our_word, gas_word))

    print("-" * 46)
    if failures:
        print(f"ENCODER CROSS-CHECK FAILED for {len(failures)} instruction(s):")
        for mnemonic, ours, our_word, gas_word in failures:
            print(f"  {mnemonic:<10} '{ours}' ours=0x{our_word:08x} gas=0x{gas_word:08x}")
        return 1

    print(f"all {len(CHECKS)} instructions match the GNU assembler")
    return 0


if __name__ == "__main__":
    sys.exit(main())
