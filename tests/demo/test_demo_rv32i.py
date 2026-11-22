"""Lockstep differential verification of the RV32I core.

The RTL (``riscv_top``) executes ``rv32i_demo.s`` -- a program that uses all
37 implemented RV32I instructions -- while a Python reference model
(``rv32i_ref.py``) executes the very same instruction stream.

After every instruction the test compares:

* the program counter
* the fetched instruction word
* all 31 writable registers
* every byte written to data memory

A mismatch fails the test immediately with the offending instruction.
"""

import os

import cocotb
from cocotb import log
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from rv32i_ref import ReferenceModel, read_mem_file

MAX_STEPS = 200


def read_int(signal):
    """Integer value of a signal, tolerating cocotb's string representation."""
    try:
        return int(signal.value)
    except Exception:
        return int(str(signal.value).replace("_", ""), 2)


@cocotb.test()
async def test_rv32i_demo(dut):
    mem_path = os.environ["IMEM_HEX_PATH"]
    words = read_mem_file(mem_path)
    log.info(f"loaded {len(words)} instruction words from {mem_path}")

    model = ReferenceModel(words)

    # ---- reset ----
    cocotb.start_soon(Clock(dut.clk, 1, "ns").start())
    dut.rst.value = 1
    await RisingEdge(dut.clk)  # program counter -> 0
    dut.rst.value = 0

    # the register file and memories have no reset, clear them by hand.
    # These writes do not advance simulation time, so no clock edge passes.
    for index in range(1, 32):
        dut.reg_file.registers[index].value = 0
    for index in range(128):
        dut.data_mem.memory[index].value = 0
    await Timer(1, "step")  # zero delay: settle the writes, no clock edge

    assert read_int(dut.pc_val) == 0, "program counter did not reset to 0"

    trace = []
    halted = False

    for step in range(MAX_STEPS):
        pc = read_int(dut.pc_val)
        word = read_int(dut.instruction)

        expected = model.step()

        assert pc == expected.pc, (
            f"step {step}: DUT pc 0x{pc:08x} != model pc 0x{expected.pc:08x}"
        )
        assert word == expected.word, (
            f"step {step} @0x{pc:08x}: DUT fetched 0x{word:08x}, "
            f"model has 0x{expected.word:08x}"
        )

        # snapshot the decode/execute internals while this instruction is on the bus
        internals = {
            "opcode": read_int(dut.alu_ctrl.opcode),
            "funct3": read_int(dut.alu_ctrl.funct3),
            "funct7": read_int(dut.alu_ctrl.funct7),
            "alu_op": read_int(dut.alu.alu_op),
            "A": read_int(dut.alu.A),
            "B": read_int(dut.alu.B),
        }

        await RisingEdge(dut.clk)
        await Timer(1, "step")  # zero delay: let the write-back settle

        for reg in range(1, 32):
            got = read_int(dut.reg_file.registers[reg])
            assert got == expected.regs[reg], (
                f"step {step} @0x{expected.pc:08x} '{expected.mnemonic}': "
                f"x{reg} = 0x{got:08x}, expected 0x{expected.regs[reg]:08x} "
                f"| internals {internals}"
            )

        for addr in expected.mem_touched:
            got = read_int(dut.data_mem.memory[addr])
            assert got == model.mem[addr], (
                f"step {step} @0x{expected.pc:08x} '{expected.mnemonic}': "
                f"M[0x{addr:x}] = 0x{got:02x}, expected 0x{model.mem[addr]:02x}"
            )

        trace.append((expected.pc, expected.word, expected.mnemonic, expected.effect))

        if model.pc == expected.pc:  # self loop -> program end
            halted = True
            break

    assert halted, "program did not reach its halt loop"

    # ---------------- report ----------------
    log.info("=" * 78)
    log.info("RV32I DEMO EXECUTION TRACE  (core vs. reference model)")
    log.info("=" * 78)
    log.info(f"{'#':>3}  {'PC':>10}  {'WORD':>10}  {'INSTRUCTION':<26} RESULT")
    for index, (pc, word, mnemonic, effect) in enumerate(trace, start=1):
        log.info(f"{index:>3}  0x{pc:08x}  0x{word:08x}  {mnemonic:<26} {effect}")

    log.info("-" * 78)
    log.info("final register file:")
    for reg in range(1, 32):
        log.info(f"  x{reg:<2} = 0x{model.regs[reg]:08x}")

    checksum = model.word_at(64)
    log.info(f"checksum M[0x40] = 0x{checksum:08x} (expected 0x00000110)")
    assert checksum == 0x110, f"checksum mismatch: 0x{checksum:08x}"

    log.info(f"executed {len(trace)} instructions, RTL and reference model agree")
    log.info("=" * 78)
