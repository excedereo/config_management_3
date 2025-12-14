import click

# SPECS описывает бинарный формат команд УВМ.
# Формат записи:
# "OP": (A, size_bytes, fields, print_order)
#
# A          код операции (попадает в биты 0..3)
# size_bytes размер команды в байтах
# fields     список полей, которые надо упаковать в число команды:
#            (имя_поля, shift, bits, kind)
#            shift: с какого бита начинается поле
#            bits:  сколько бит занимает поле
#            kind:  "reg" (аргумент регистр rN) или "imm" (обычное число)
# print_order порядок вывода полей в режиме --test
SPECS = {
    "LC":  (0, 4, [("B", 4, 7, "reg"), ("C", 11, 20, "imm")], ["A", "B", "C"]),
    "LDM": (13, 5, [("B", 4, 15, "imm"), ("C", 19, 7, "reg"), ("D", 26, 7, "reg")], ["A", "B", "C", "D"]),
    "STM": (9, 3, [("B", 4, 10, "imm"), ("C", 14, 7, "reg")], ["A", "B", "C"]),
    "GE":  (15, 4, [("B", 4, 7, "reg"), ("C", 11, 10, "imm"), ("D", 21, 7, "reg")], ["A", "B", "C", "D"]),
}

# Алиасы для удобных длинных названий команд
ALIASES = {
    "LOAD_CONST": "LC", "LC": "LC",
    "LOAD_MEM": "LDM",  "LDM": "LDM",
    "STORE_MEM": "STM", "STM": "STM",
    "CMP_GE": "GE",     "GE": "GE",
}

def clean(line: str) -> str:
    # Удаляем комментарии и лишние пробелы
    return line.split(";", 1)[0].split("#", 1)[0].strip()

def num(t: str) -> int:
    # Понимает 123, -5, 0xFF
    return int(t, 0)

def reg(t: str) -> int:
    # r72 -> 72, также допускается просто 72
    t = t.strip()
    if t[:1].lower() == "r":
        t = t[1:]
    return num(t)

def fit_bits(x: int, bits: int) -> int:
    # Упаковка отрицательных значений в доп.код (two's complement),
    # чтобы можно было писать отрицательные смещения
    if x < 0:
        x = (1 << bits) + x
    if not (0 <= x < (1 << bits)):
        raise ValueError(f"{x} не влезает в {bits} бит")
    return x

def parse(line: str, n: int):
    line = clean(line)
    if not line:
        return None

    parts = line.replace(",", " ").split()
    mnem = parts[0].upper()
    if mnem not in ALIASES:
        raise ValueError(f"строка {n}: неизвестная команда {mnem}")

    op = ALIASES[mnem]
    A, size, fields, order = SPECS[op]
    args = parts[1:]

    # В языке делаем понятный порядок аргументов:
    # LOAD_MEM rC, rD, B
    # CMP_GE   rD, rB, C
    #
    # Но в бинарном формате поля идут в другом порядке, поэтому тут переставляем:
    # LDM: B, C, D
    # GE:  B, C, D
    if op == "LDM":
        if len(args) != 3:
            raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[2], args[0], args[1]]
    elif op == "GE":
        if len(args) != 3:
            raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[1], args[2], args[0]]

    if len(args) != len(fields):
        raise ValueError(f"строка {n}: неверно аргументов")

    ins = {"op": op, "A": A}
    code = A  # A всегда лежит в битах 0..3

    # Упаковка: кладём каждое поле в нужные биты и склеиваем через OR
    for a, (name, shift, bits, kind) in zip(args, fields):
        v = reg(a) if kind == "reg" else num(a)
        ins[name] = v
        code |= fit_bits(v, bits) << shift

    # Переводим итоговое число команды в байты little-endian
    ins["bytes"] = list(code.to_bytes(size, "little"))
    return ins

def assemble(text: str):
    prog = []
    for i, line in enumerate(text.splitlines(), 1):
        ins = parse(line, i)
        if ins:
            prog.append(ins)
    return prog

def show(prog):
    # Печать как в спецификации: поля и итоговые байты
    for ins in prog:
        order = SPECS[ins["op"]][3]
        click.echo("Тест (" + ", ".join(f"{k}={ins[k]}" for k in order) + "):")
        click.echo(", ".join(f"0x{b:02X}" for b in ins["bytes"]))

@click.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False))
@click.argument("out", type=click.Path(dir_okay=False))
@click.option("--test", is_flag=True)
def main(src, out, test):
    prog = assemble(open(src, "r", encoding="utf-8").read())
    data = bytearray(b for ins in prog for b in ins["bytes"])
    open(out, "wb").write(data)
    if test:
        show(prog)

if __name__ == "__main__":
    main()
