"""Build and run the RV32I demonstration.

1. assembles ``rv32i_demo.s`` with the bare-metal RISC-V toolchain
2. converts the binary into a word-per-line ``.mem`` image
3. runs the cocotb lockstep test (RTL core vs. Python reference model)

Usage:  cd tests/demo && uv run python run_demo.py
"""

import pathlib
import shutil
import subprocess

from cocotb_tools.runner import get_runner

import check_encoder

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILD = HERE / "build"


def tool(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(f"none of {names} found in PATH")


def build_program():
    BUILD.mkdir(exist_ok=True)
    source = HERE / "rv32i_demo.s"
    elf = BUILD / "rv32i_demo.elf"
    binary = BUILD / "rv32i_demo.bin"
    mem = BUILD / "rv32i_demo.mem"

    subprocess.run(
        [
            tool("riscv64-unknown-elf-as", "riscv64-elf-as"),
            "-march=rv32i",
            "-mabi=ilp32",
            "-o",
            str(elf),
            str(source),
        ],
        check=True,
    )
    subprocess.run(
        [
            tool("riscv64-unknown-elf-objcopy", "riscv64-elf-objcopy"),
            "-O",
            "binary",
            str(elf),
            str(binary),
        ],
        check=True,
    )

    data = binary.read_bytes()
    words = [
        int.from_bytes(data[index:index + 4], "little")
        for index in range(0, len(data), 4)
    ]
    mem.write_text("\n".join(f"{word:08x}" for word in words) + "\n")

    listing = subprocess.run(
        [tool("riscv64-unknown-elf-objdump", "riscv64-elf-objdump"), "-d", str(elf)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (BUILD / "rv32i_demo.lst").write_text(listing)

    print(f"assembled {len(words)} instructions -> {mem}")
    return mem


def main():
    # the test-side encoder must agree with the GNU assembler for every
    # instruction the tests use (guards against silent mis-encoding)
    if check_encoder.main() != 0:
        raise SystemExit("encoder cross-check failed")

    mem = build_program()

    sources = sorted(str(path) for path in (ROOT / "rtl" / "riscv").glob("*.v"))
    runner = get_runner("icarus")

    runner.build(
        sources=sources,
        hdl_toplevel="riscv_top",
        includes=[str(ROOT / "rtl" / "include")],
        defines={"IMEM_LOAD_HEX": "1", "IMEM_HEX_PATH": str(mem)},
        clean=True,
        waves=True,
    )
    runner.test(
        hdl_toplevel="riscv_top",
        test_module="test_demo_rv32i",
        waves=True,
        extra_env={"IMEM_HEX_PATH": str(mem), "PYTHONPATH": str(HERE)},
    )


if __name__ == "__main__":
    main()
