import csv
import click

SIZES = {0: 4, 9: 3, 13: 5, 15: 4}

def to_signed(x: int, bits: int) -> int:
    if x >= (1 << (bits - 1)):
        x -= (1 << bits)
    return x

def decode(opcode: int, raw: bytes) -> dict:
    code = int.from_bytes(raw, "little")

    if opcode == 0:  # LC
        B = (code >> 4) & 0x7F
        C = to_signed((code >> 11) & ((1 << 20) - 1), 20)
        return {"op": "LC", "B": B, "C": C}

    if opcode == 9:  # STM
        B = (code >> 4) & 0x3FF
        C = (code >> 14) & 0x7F
        return {"op": "STM", "B": B, "C": C}

    if opcode == 13:  # LDM
        B = to_signed((code >> 4) & ((1 << 15) - 1), 15)
        C = (code >> 19) & 0x7F
        D = (code >> 26) & 0x7F
        return {"op": "LDM", "B": B, "C": C, "D": D}

    return {"op": "UNKNOWN", "A": opcode}

def run_program(mem: list[int], prog_len: int) -> None:
    regs = [0] * 128
    pc = 0

    while pc < prog_len:
        opcode = mem[pc] & 0x0F
        if opcode not in SIZES:
            raise ValueError(f"Неизвестная команда A={opcode} по адресу {pc}")

        size = SIZES[opcode]
        raw = bytes((mem[pc + i] & 0xFF) for i in range(size))
        ins = decode(opcode, raw)

        if ins["op"] == "LC":
            regs[ins["B"]] = ins["C"]

        elif ins["op"] == "STM":
            mem[ins["B"]] = regs[ins["C"]]

        elif ins["op"] == "LDM":
            addr = regs[ins["D"]] + ins["B"]
            if not (0 <= addr < len(mem)):
                raise ValueError(f"Выход за память: {addr}")
            regs[ins["C"]] = mem[addr]

        else:
            raise NotImplementedError(f"Команда A={opcode} не реализована на этапе 3")

        pc += size

def dump_memory(mem: list[int], start: int, end: int, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["address", "value"])
        for a in range(start, end + 1):
            w.writerow([a, mem[a]])

@click.command()
@click.argument("program_bin", type=click.Path(exists=True, dir_okay=False))
@click.argument("dump_csv", type=click.Path(dir_okay=False))
@click.argument("mem_range")  # start:end
def main(program_bin, dump_csv, mem_range):
    a, b = mem_range.split(":")
    start, end = int(a, 0), int(b, 0)

    prog = open(program_bin, "rb").read()
    mem = [0] * max(4096, len(prog) + 2048)

    for i, byte in enumerate(prog):
        mem[i] = byte

    run_program(mem, len(prog))
    dump_memory(mem, start, end, dump_csv)

if __name__ == "__main__":
    main()
