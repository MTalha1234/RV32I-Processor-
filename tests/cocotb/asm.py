"""Minimal RV32I encoder used by the cocotb tests.

This replaces the `riscv_assembler` package, which mis-encodes `srai`
(funct7 = 0, i.e. an `srli`) and does not support `srli` at all. Because such
an encoding error is silent -- the test still "passes" while checking the
wrong instruction -- every encoding produced here is cross-checked against the
GNU assembler by `tests/demo/check_encoder.py`.

Operand forms (registers may be written `xN` or with their ABI name):

  R-type   add sub sll slt sltu xor srl sra or and    rd, rs1, rs2
  I-type   addi slti sltiu xori ori andi             rd, rs1, imm
  I-shift  slli srli srai                            rd, rs1, shamt
  Load     lb lh lw lbu lhu                         rd, imm(rs1)
  Store    sb sh sw                                 rs2, imm(rs1)
  Branch   beq bne blt bge bltu bgeu                rs1, rs2, offset
  Jump     jal                                       rd, offset
  JumpR    jalr                                      rd, imm(rs1)
  Upper    lui auipc                                 rd, imm20

`offset` is a byte offset relative to the instruction, matching the encoding
of a branch/jump displacement.
"""

import re

REGISTERS = {f"x{index}": index for index in range(32)}
REGISTERS.update(
    {
        "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
        "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
        "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
        "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21,
        "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
        "t3": 28, "t4": 29, "t5": 30, "t6": 31,
    }
)

# opcode, funct3, funct7 (None = funct3 only)
FORMATS = {
    "add": (0x33, 0, 0x00),
    "sub": (0x33, 0, 0x20),
    "sll": (0x33, 1, 0x00),
    "slt": (0x33, 2, None),
    "sltu": (0x33, 3, None),
    "xor": (0x33, 4, None),
    "srl": (0x33, 5, 0x00),
    "sra": (0x33, 5, 0x20),
    "or": (0x33, 6, None),
    "and": (0x33, 7, None),
    "addi": (0x13, 0, None),
    "slti": (0x13, 2, None),
    "sltiu": (0x13, 3, None),
    "xori": (0x13, 4, None),
    "ori": (0x13, 6, None),
    "andi": (0x13, 7, None),
    "slli": (0x13, 1, 0x00),
    "srli": (0x13, 5, 0x00),
    "srai": (0x13, 5, 0x20),
    "lui": (0x37, 0, None),
    "auipc": (0x17, 0, None),
    "jal": (0x6F, 0, None),
    "jalr": (0x67, 0, None),
    "beq": (0x63, 0, None),
    "bne": (0x63, 1, None),
    "blt": (0x63, 4, None),
    "bge": (0x63, 5, None),
    "bltu": (0x63, 6, None),
    "bgeu": (0x63, 7, None),
    "lb": (0x03, 0, None),
    "lh": (0x03, 1, None),
    "lw": (0x03, 2, None),
    "lbu": (0x03, 4, None),
    "lhu": (0x03, 5, None),
    "sb": (0x23, 0, None),
    "sh": (0x23, 1, None),
    "sw": (0x23, 2, None),
}

MEMORY_OPERAND = re.compile(r"^(-?(?:0x)?[0-9a-fA-F]+)\((\w+)\)$")


class EncodingError(ValueError):
    """Raised when an instruction cannot be encoded."""


def _register(name):
    try:
        return REGISTERS[name]
    except KeyError:
        raise EncodingError(f"unknown register: {name}") from None


def _number(text):
    text = text.strip()
    try:
        return int(text, 0)
    except ValueError:
        raise EncodingError(f"not a number: {text}") from None


def _split(text):
    return [part for part in re.split(r"[,\s]+", text.strip()) if part]


def _memory_operand(text):
    match = MEMORY_OPERAND.match(text.strip())
    if not match:
        raise EncodingError(f"expected imm(rs1), got: {text}")
    return _number(match.group(1)), _register(match.group(2))


def _signed(value, bits):
    limit = 1 << (bits - 1)
    if not -limit <= value < limit:
        raise EncodingError(f"immediate {value} does not fit in {bits} bits")
    return value & ((1 << bits) - 1)


def encode(text):
    """Encode one RV32I instruction and return its 32-bit word."""
    parts = _split(text)
    if not parts:
        raise EncodingError("empty instruction")

    mnemonic, args = parts[0], parts[1:]
    if mnemonic not in FORMATS:
        raise EncodingError(f"unsupported instruction: {mnemonic}")

    opcode, funct3, funct7 = FORMATS[mnemonic]

    if mnemonic in ("lui", "auipc"):
        if len(args) != 2:
            raise EncodingError(f"{mnemonic} expects rd, imm20")
        rd = _register(args[0])
        imm20 = _number(args[1]) & 0xFFFFF
        return (imm20 << 12) | (rd << 7) | opcode

    if mnemonic == "jal":
        if len(args) != 2:
            raise EncodingError("jal expects rd, offset")
        rd = _register(args[0])
        offset = _signed(_number(args[1]), 21)
        imm = (
            ((offset >> 20) & 0x1) << 31
            | ((offset >> 1) & 0x3FF) << 21
            | ((offset >> 11) & 0x1) << 20
            | ((offset >> 12) & 0xFF) << 12
        )
        return imm | (rd << 7) | opcode

    if mnemonic == "jalr":
        if len(args) != 2:
            raise EncodingError("jalr expects rd, imm(rs1)")
        rd = _register(args[0])
        imm, rs1 = _memory_operand(args[1])
        return (_signed(imm, 12) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    if mnemonic in ("beq", "bne", "blt", "bge", "bltu", "bgeu"):
        if len(args) != 3:
            raise EncodingError(f"{mnemonic} expects rs1, rs2, offset")
        rs1 = _register(args[0])
        rs2 = _register(args[1])
        offset = _signed(_number(args[2]), 13)
        imm = (
            ((offset >> 12) & 0x1) << 31
            | ((offset >> 5) & 0x3F) << 25
            | ((offset >> 1) & 0xF) << 8
            | ((offset >> 11) & 0x1) << 7
        )
        return imm | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | opcode

    if mnemonic in ("lb", "lh", "lw", "lbu", "lhu"):
        if len(args) != 2:
            raise EncodingError(f"{mnemonic} expects rd, imm(rs1)")
        rd = _register(args[0])
        imm, rs1 = _memory_operand(args[1])
        return (_signed(imm, 12) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    if mnemonic in ("sb", "sh", "sw"):
        if len(args) != 2:
            raise EncodingError(f"{mnemonic} expects rs2, imm(rs1)")
        rs2 = _register(args[0])
        imm, rs1 = _memory_operand(args[1])
        imm = _signed(imm, 12)
        return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | ((imm & 0x1F) << 7) | opcode

    if mnemonic in ("slli", "srli", "srai"):
        if len(args) != 3:
            raise EncodingError(f"{mnemonic} expects rd, rs1, shamt")
        rd = _register(args[0])
        rs1 = _register(args[1])
        shamt = _number(args[2])
        if not 0 <= shamt <= 31:
            raise EncodingError(f"shift amount out of range: {shamt}")
        return (
            (funct7 << 25)
            | (shamt << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | opcode
        )

    if mnemonic in ("addi", "slti", "sltiu", "xori", "ori", "andi"):
        if len(args) != 3:
            raise EncodingError(f"{mnemonic} expects rd, rs1, imm")
        rd = _register(args[0])
        rs1 = _register(args[1])
        imm = _signed(_number(args[2]), 12)
        return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    # R-type
    if len(args) != 3:
        raise EncodingError(f"{mnemonic} expects rd, rs1, rs2")
    rd = _register(args[0])
    rs1 = _register(args[1])
    rs2 = _register(args[2])
    return (
        ((funct7 or 0) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (rd << 7)
        | opcode
    )
