import csv
import click

# Размер команды зависит от A (opcode), это нужно для чтения байт из памяти.
SIZES = {0: 4, 9: 3, 13: 5, 15: 4}

def to_signed(x: int, bits: int) -> int:
    # Преобразование из unsigned в signed для полей, где допускаются отрицательные.
    if x >= (1 << (bits - 1)):
        x -= (1 << bits)
    return x

def decode(opcode: int, raw: bytes) -> dict:
    # Декодирование байт команды в поля B,C,D по спецификации.
    code = int.from_bytes(raw, "little")

    if opcode == 0:  # LC: B(4..10), C(11..30)
        B = (code >> 4) & 0x7F
        C = to_signed((code >> 11) & ((1 << 20) - 1), 20)
        return {"op": "LC", "B": B, "C": C}

    if opcode == 9:  # STM: B(4..13), C(14..20)
        B = (code >> 4) & 0x3FF
        C = (code >> 14) & 0x7F
        return {"op": "STM", "B": B, "C": C}

    if opcode == 13:  # LDM: B(4..18 signed), C(19..25), D(26..32)
        B = to_signed((code >> 4) & ((1 << 15) - 1), 15)
        C = (code >> 19) & 0x7F
        D = (code >> 26) & 0x7F
        return {"op": "LDM", "B": B, "C": C, "D": D}

    if opcode == 15:  # GE: B(4..10), C(11..20), D(21..27)
        B = (code >> 4) & 0x7F
        C = (code >> 11) & 0x3FF
        D = (code >> 21) & 0x7F
        return {"op": "GE", "B": B, "C": C, "D": D}

    return {"op": "UNKNOWN", "A": opcode}

def run_program(mem: list[int], prog_len: int) -> None:
    # Регистр-файл. r0..r127.
    regs = [0] * 128

    # pc указывает на байт команды в общей памяти.
    pc = 0

    # Главный цикл интерпретации: fetch -> decode -> execute.
    while pc < prog_len:
        opcode = mem[pc] & 0x0F
        if opcode not in SIZES:
            raise ValueError(f"Неизвестная команда A={opcode} по адресу {pc}")

        size = SIZES[opcode]
        raw = bytes((mem[pc + i] & 0xFF) for i in range(size))
        ins = decode(opcode, raw)

        # Выполнение команд.
        if ins["op"] == "LC":
            regs[ins["B"]] = ins["C"]

        elif ins["op"] == "STM":
            # MEM[B] = rC
            mem[ins["B"]] = regs[ins["C"]]

        elif ins["op"] == "LDM":
            # rC = MEM[rD + B]
            addr = regs[ins["D"]] + ins["B"]
            if not (0 <= addr < len(mem)):
                raise ValueError(f"Выход за память: {addr}")
            regs[ins["C"]] = mem[addr]

        elif ins["op"] == "GE":
            # rD = (rB >= MEM[C]) ? 1 : 0
            regs[ins["D"]] = 1 if regs[ins["B"]] >= mem[ins["C"]] else 0

        else:
            raise NotImplementedError(f"Команда A={opcode} не реализована")

        pc += size

def dump_memory(mem: list[int], start: int, end: int, path: str) -> None:
    # CSV дамп памяти: address,value
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
    # Диапазон дампа берём из аргумента командной строки.
    a, b = mem_range.split(":")
    start, end = int(a, 0), int(b, 0)

    # Загружаем программу в начало общей памяти.
    prog = open(program_bin, "rb").read()
    mem = [0] * max(4096, len(prog) + 2048)
    for i, byte in enumerate(prog):
        mem[i] = byte

    # Выполняем только область программы (0..len(prog)-1).
    run_program(mem, len(prog))

    # После выполнения сохраняем дамп выбранного диапазона.
    dump_memory(mem, start, end, dump_csv)

if __name__ == "__main__":
    main()
