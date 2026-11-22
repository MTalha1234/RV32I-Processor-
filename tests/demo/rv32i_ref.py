"""Minimal RV32I reference model + disassembler.

Mirrors the semantics of the RTL in ``rtl/riscv`` exactly:

* 32-bit registers, ``x0`` hard-wired to zero (``register_file.v``)
* byte-addressed, little-endian data memory (``data_memory.v``)
* PC-relative branches/jumps, target forced to even address (``riscv_top.v``)
* logical vs. arithmetic right shift distinguished by funct7 (``alu_control.v``)

Used by ``tests/demo/test_demo_rv32i.py`` to check the RTL instruction by
instruction while the core is running.
"""

MASK = 0xFFFFFFFF
DATA_MEM_SIZE = 2048

REG_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1",
    "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7",
    "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11",
    "t3", "t4", "t5", "t6",
]

OP_NAMES = {
    0x37: "lui", 0x17: "auipc", 0x6F: "jal", 0x67: "jalr",
    0x63: "branch", 0x03: "load", 0x23: "store", 0x13: "op-imm", 0x33: "op",
}

ALU_IMM_NAMES = ["addi", "slli", "slti", "sltiu", "xori", "srli", "ori", "andi"]
ALU_REG_NAMES = ["add", "sll", "slt", "sltu", "xor", "srl", "or", "and"]
BRANCH_NAMES = ["beq", "bne", "?", "?", "blt", "bge", "bltu", "bgeu"]
LOAD_NAMES = ["lb", "lh", "lw", "?", "lbu", "lhu", "?", "?"]
STORE_NAMES = ["sb", "sh", "sw", "?", "?", "?", "?", "?"]


def u32(value):
    return value & MASK


def s32(value):
    value &= MASK
    return value - (1 << 32) if value & 0x80000000 else value


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def read_mem_file(path):
    """Read a $readmemh-style file into a list of 32-bit words."""
    words = []
    with open(path) as handle:
        for line in handle:
            line = line.split("//")[0].strip()
            if not line:
                continue
            words.append(int(line, 16) & MASK)
    return words


class Step:
    """Result of executing one instruction."""

    def __init__(self, pc, word, mnemonic, effect, regs, mem_touched):
        self.pc = pc
        self.word = word
        self.mnemonic = mnemonic
        self.effect = effect
        self.regs = regs
        self.mem_touched = mem_touched


class ReferenceModel:
    def __init__(self, words, mem_size=DATA_MEM_SIZE):
        self.words = list(words)
        self.regs = [0] * 32
        self.mem = bytearray(mem_size)
        self.pc = 0

    # ------------------------------------------------------------------ utils
    def fetch(self, pc):
        index = pc >> 2
        return self.words[index] if 0 <= index < len(self.words) else 0

    def _rd(self, rd, value, effect):
        if rd:
            self.regs[rd] = u32(value)
        return effect

    # ------------------------------------------------------------------ step
    def step(self):
        pc = self.pc
        word = self.fetch(pc)
        opcode = word & 0x7F
        rd = (word >> 7) & 0x1F
        funct3 = (word >> 12) & 7
        rs1 = (word >> 15) & 0x1F
        rs2 = (word >> 20) & 0x1F
        funct7 = (word >> 25) & 0x7F
        a = self.regs[rs1]
        b = self.regs[rs2]
        next_pc = u32(pc + 4)
        effect = ""
        mem_touched = []

        if opcode == 0x37:  # LUI
            value = u32(word & 0xFFFFF000)
            effect = self._rd(rd, value, f"x{rd} = 0x{value:08x}")
            mnemonic = f"lui x{rd}, 0x{(word >> 12) & 0xFFFFF:x}"

        elif opcode == 0x17:  # AUIPC
            value = u32(pc + (word & 0xFFFFF000))
            effect = self._rd(rd, value, f"x{rd} = 0x{value:08x}")
            mnemonic = f"auipc x{rd}, 0x{(word >> 12) & 0xFFFFF:x}"

        elif opcode == 0x6F:  # JAL
            imm = sext(
                (((word >> 31) & 1) << 20)
                | (((word >> 12) & 0xFF) << 12)
                | (((word >> 20) & 1) << 11)
                | (((word >> 21) & 0x3FF) << 1),
                21,
            )
            link = u32(pc + 4)
            next_pc = u32(u32(pc + imm) & ~1)
            effect = self._rd(
                rd,
                link,
                f"x{rd} = 0x{link:08x}, pc -> 0x{next_pc:08x}"
                if rd
                else f"no link write (x0), pc -> 0x{next_pc:08x}",
            )
            mnemonic = f"jal x{rd}, 0x{next_pc:08x}"

        elif opcode == 0x67:  # JALR
            imm = sext(word >> 20, 12)
            link = u32(pc + 4)
            next_pc = u32(u32(a + imm) & ~1)
            effect = self._rd(
                rd,
                link,
                f"x{rd} = 0x{link:08x}, pc -> 0x{next_pc:08x}"
                if rd
                else f"no link write (x0), pc -> 0x{next_pc:08x}",
            )
            mnemonic = f"jalr x{rd}, {imm}(x{rs1})"

        elif opcode == 0x63:  # BRANCH
            imm = sext(
                (((word >> 31) & 1) << 12)
                | (((word >> 7) & 1) << 11)
                | (((word >> 25) & 0x3F) << 5)
                | (((word >> 8) & 0xF) << 1),
                13,
            )
            taken = {
                0: a == b,
                1: a != b,
                4: s32(a) < s32(b),
                5: s32(a) >= s32(b),
                6: a < b,
                7: a >= b,
            }[funct3]
            if taken:
                next_pc = u32(u32(pc + imm) & ~1)
            effect = (
                f"{'taken' if taken else 'not taken'}"
                + (f", pc -> 0x{next_pc:08x}" if taken else f", pc -> 0x{next_pc:08x}")
            )
            mnemonic = f"{BRANCH_NAMES[funct3]} x{rs1}, x{rs2}, 0x{u32(pc + imm) & ~1:08x}"

        elif opcode == 0x03:  # LOAD
            imm = sext(word >> 20, 12)
            addr = u32(a + imm)
            if funct3 == 0:
                value = u32(sext(self.mem[addr], 8))
            elif funct3 == 1:
                value = u32(sext(self.mem[addr] | (self.mem[addr + 1] << 8), 16))
            elif funct3 == 2:
                value = u32(
                    self.mem[addr]
                    | (self.mem[addr + 1] << 8)
                    | (self.mem[addr + 2] << 16)
                    | (self.mem[addr + 3] << 24)
                )
            elif funct3 == 4:
                value = self.mem[addr]
            elif funct3 == 5:
                value = self.mem[addr] | (self.mem[addr + 1] << 8)
            else:
                raise ValueError(f"illegal load funct3={funct3}")
            effect = self._rd(rd, value, f"x{rd} = 0x{value:08x}  (M[0x{addr:x}])")
            mnemonic = f"{LOAD_NAMES[funct3]} x{rd}, {imm}(x{rs1})"

        elif opcode == 0x23:  # STORE
            imm = sext(((word >> 25) << 5) | ((word >> 7) & 0x1F), 12)
            addr = u32(a + imm)
            if funct3 == 0:
                self.mem[addr] = b & 0xFF
                mem_touched = [addr]
            elif funct3 == 1:
                self.mem[addr] = b & 0xFF
                self.mem[addr + 1] = (b >> 8) & 0xFF
                mem_touched = [addr, addr + 1]
            elif funct3 == 2:
                self.mem[addr] = b & 0xFF
                self.mem[addr + 1] = (b >> 8) & 0xFF
                self.mem[addr + 2] = (b >> 16) & 0xFF
                self.mem[addr + 3] = (b >> 24) & 0xFF
                mem_touched = [addr, addr + 1, addr + 2, addr + 3]
            else:
                raise ValueError(f"illegal store funct3={funct3}")
            effect = f"M[0x{addr:x}] = 0x{b:08x}"
            mnemonic = f"{STORE_NAMES[funct3]} x{rs2}, {imm}(x{rs1})"

        elif opcode == 0x13:  # OP-IMM
            imm = sext(word >> 20, 12)
            if funct3 == 0:
                value = u32(a + imm)
            elif funct3 == 1:
                value = u32(a << ((word >> 20) & 0x1F))
            elif funct3 == 2:
                value = 1 if s32(a) < s32(imm) else 0
            elif funct3 == 3:
                value = 1 if a < u32(imm) else 0
            elif funct3 == 4:
                value = u32(a ^ u32(imm))
            elif funct3 == 5:
                shamt = (word >> 20) & 0x1F
                value = u32(a >> shamt) if funct7 == 0 else u32(s32(a) >> shamt)
            elif funct3 == 6:
                value = u32(a | u32(imm))
            else:
                value = u32(a & u32(imm))
            effect = self._rd(rd, value, f"x{rd} = 0x{value:08x}")
            if funct3 == 5:
                shamt = (word >> 20) & 0x1F
                name = "srli" if funct7 == 0 else "srai"
                mnemonic = f"{name} x{rd}, x{rs1}, {shamt}"
            elif funct3 == 1:
                mnemonic = f"slli x{rd}, x{rs1}, {(word >> 20) & 0x1F}"
            else:
                mnemonic = f"{ALU_IMM_NAMES[funct3]} x{rd}, x{rs1}, {imm}"

        elif opcode == 0x33:  # OP
            if funct3 == 0:
                value = u32(a + b) if funct7 == 0 else u32(a - b)
            elif funct3 == 1:
                value = u32(a << (b & 0x1F))
            elif funct3 == 2:
                value = 1 if s32(a) < s32(b) else 0
            elif funct3 == 3:
                value = 1 if a < b else 0
            elif funct3 == 4:
                value = u32(a ^ b)
            elif funct3 == 5:
                shamt = b & 0x1F
                value = u32(a >> shamt) if funct7 == 0 else u32(s32(a) >> shamt)
            elif funct3 == 6:
                value = u32(a | b)
            else:
                value = u32(a & b)
            effect = self._rd(rd, value, f"x{rd} = 0x{value:08x}")
            if funct3 == 5:
                name = "srl" if funct7 == 0 else "sra"
                mnemonic = f"{name} x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0:
                name = "add" if funct7 == 0 else "sub"
                mnemonic = f"{name} x{rd}, x{rs1}, x{rs2}"
            else:
                mnemonic = f"{ALU_REG_NAMES[funct3]} x{rd}, x{rs1}, x{rs2}"

        else:
            raise ValueError(f"illegal opcode 0x{opcode:02x} at pc 0x{pc:08x}")

        self.pc = next_pc
        return Step(pc, word, mnemonic, effect, list(self.regs), mem_touched)

    # ------------------------------------------------------------------ report
    def word_at(self, addr):
        return int.from_bytes(self.mem[addr:addr + 4], "little")
