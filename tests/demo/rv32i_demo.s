# rv32i_demo.s -- exercises all 37 implemented RV32I instructions
#
# Assembled with the bare-metal toolchain and executed on the RTL core by
# tests/demo/run_demo.py. Every instruction below is checked against the
# Python reference model in tests/demo/rv32i_ref.py, instruction by
# instruction, while the core is running.

    .text
    .globl _start
_start:
    # ---------------- setup ----------------
    addi  x1,  x0, 10            # x1 = 10
    addi  x2,  x0, -20           # x2 = -20 (0xFFFFFFEC)
    addi  x3,  x0, 7             # x3 = 7
    lui   x4,  0x12345           # x4 = 0x12345000
    auipc x5,  0                 # x5 = address of this instruction

    # ---------------- I-type ALU ----------------
    addi  x6,  x1, 7             # 17
    slti  x7,  x2, 10            # 1  (signed:   -20 < 10)
    sltiu x8,  x2, 10            # 0  (unsigned: 0xFFFFFFEC > 10)
    xori  x9,  x1, 0xF           # 5
    ori   x10, x1, 0x30          # 58
    andi  x11, x1, 0x3           # 2
    slli  x12, x1, 3             # 80
    srli  x13, x2, 1             # 0x7FFFFFF6  (logical)
    srai  x14, x2, 1             # 0xFFFFFFF6  (arithmetic)

    # ---------------- R-type ALU ----------------
    add   x15, x1, x3            # 17
    sub   x16, x3, x1            # -3
    sll   x17, x1, x3            # 1280
    slt   x18, x2, x1            # 1
    sltu  x19, x2, x1            # 0
    xor   x20, x1, x3            # 13
    srl   x21, x2, x3            # 0x01FFFFFF
    sra   x22, x2, x3            # 0xFFFFFFFF
    or    x23, x1, x3            # 15
    and   x24, x1, x3            # 2

    # ---------------- stores & loads ----------------
    sw    x1, 0(x0)              # M[0:4]  = 0x0000000A
    lw    x25, 0(x0)             # 0x0000000A
    lb    x26, 0(x0)             # 0x0000000A
    lbu   x27, 0(x0)             # 0x0000000A
    lh    x28, 0(x0)             # 0x0000000A
    lhu   x29, 0(x0)             # 0x0000000A
    sw    x2, 4(x0)              # M[4:8]  = 0xFFFFFFEC
    sh    x2, 8(x0)              # M[8:10] = 0xFFEC
    sb    x2, 12(x0)             # M[12]   = 0xEC
    lw    x25, 4(x0)             # 0xFFFFFFEC
    lb    x26, 4(x0)             # 0xFFFFFFEC  (sign extended 0xEC)
    lbu   x27, 4(x0)             # 0x000000EC
    lh    x28, 4(x0)             # 0xFFFFFFEC  (sign extended 0xFFEC)
    lhu   x29, 4(x0)             # 0x0000FFEC

    # ---------------- branches: taken and not-taken ----------------
    beq   x1, x2, L1             # not taken (10 != -20)
    addi  x30, x0, 0x11          # executed
L1:
    bne   x1, x1, L2             # not taken (10 == 10)
    addi  x30, x0, 0x22          # executed
L2:
    blt   x2, x1, L3             # taken (-20 < 10)
    addi  x30, x0, 0x33          # skipped
L3:
    bge   x1, x2, L4             # taken (10 >= -20)
    addi  x30, x0, 0x44          # skipped
L4:
    bltu  x2, x1, L5             # not taken (unsigned 0xFFFFFFEC > 10)
    addi  x30, x0, 0x55          # executed
L5:
    bgeu  x2, x1, L6             # taken (unsigned 0xFFFFFFEC >= 10)
    addi  x30, x0, 0x66          # skipped
L6:
    bne   x1, x2, L7             # taken (10 != -20)
    addi  x30, x0, 0x77          # skipped
L7:
    beq   x1, x1, L8             # taken (10 == 10)
    addi  x30, x0, 0x88          # skipped
L8:
    # x30 = 0x55 at this point

    # ---------------- jumps ----------------
    jal   x28, Ljump             # x28 = pc+4, jump to Ljump
    addi  x30, x0, 0x99          # skipped
Ljump:
    auipc x26, 0                 # x26 = pc of this instruction
    addi  x26, x26, 16           # x26 = target address (pc + 16)
    jalr  x27, 0(x26)            # x27 = pc+4, jump to (x26 + 0)
    addi  x30, x0, 0xAA          # skipped
    addi  x29, x0, 0xBB          # <- jalr target, executed

    # ---------------- checksum ----------------
    add   x30, x30, x29          # x30 = 0x55 + 0xBB = 0x110
    sw    x30, 64(x0)            # M[64:68] = 0x00000110

halt:
    jal   x0, halt               # self loop -> end of program
