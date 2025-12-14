import click

# SPECS описывает формат команд из спецификации.
# "OP": (A, size_bytes, fields)
# fields: (name, shift, bits, kind)
# shift и bits нужны, чтобы упаковать поле в нужные биты команды.
SPECS = {
    "LC":  (0, 4, [("B", 4, 7, "reg"), ("C", 11, 20, "imm")]),
    "LDM": (13, 5, [("B", 4, 15, "imm"), ("C", 19, 7, "reg"), ("D", 26, 7, "reg")]),
    "STM": (9, 3, [("B", 4, 10, "imm"), ("C", 14, 7, "reg")]),
    "GE":  (15, 4, [("B", 4, 7, "reg"), ("C", 11, 10, "imm"), ("D", 21, 7, "reg")]),
}

# Алиасы, чтобы в asm можно было писать понятными словами.
ALIASES = {
    "LOAD_CONST": "LC", "LC": "LC",
    "LOAD_MEM": "LDM",  "LDM": "LDM",
    "STORE_MEM": "STM", "STM": "STM",
    "CMP_GE": "GE",     "GE": "GE",
}

def clean(s: str) -> str:
    # Убираем комментарии и лишние пробелы.
    return s.split(";", 1)[0].split("#", 1)[0].strip()

def num(t: str) -> int:
    # int(...,0) понимает 123, -5, 0xFF.
    return int(t, 0)

def reg(t: str) -> int:
    # r72 -> 72, также можно писать просто 72.
    t = t.strip()
    if t[:1].lower() == "r":
        t = t[1:]
    return num(t)

def fit_bits(x: int, bits: int) -> int:
    # Поля команды имеют ограничение по битам.
    # Если значение отрицательное, упаковываем в доп.код, чтобы влезло в bits.
    if x < 0:
        x = (1 << bits) + x
    if not (0 <= x < (1 << bits)):
        raise ValueError(f"{x} не влезает в {bits} бит")
    return x

def parse_line(line: str, n: int):
    # Разбираем одну строку asm в промежуточное представление (IR).
    # IR хранит A, B, C, D как числа, плюс значения для упаковки.
    line = clean(line)
    if not line:
        return None

    parts = line.replace(",", " ").split()
    mnem = parts[0].upper()
    if mnem not in ALIASES:
        raise ValueError(f"строка {n}: неизвестная команда {mnem}")

    op = ALIASES[mnem]
    A, _, fields = SPECS[op]
    args = parts[1:]

    # Порядок аргументов в тексте делаем понятным.
    # Но в формате команды поля идут в порядке B,C,D, поэтому переставляем.
    # LOAD_MEM rC, rD, B -> B, rC, rD
    # CMP_GE rD, rB, C   -> rB, C, rD
    if op == "LDM":
        if len(args) != 3:
            raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[2], args[0], args[1]]
    if op == "GE":
        if len(args) != 3:
            raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[1], args[2], args[0]]

    if len(args) != len(fields):
        raise ValueError(f"строка {n}: неверно аргументов")

    ins = {"op": op, "A": A}
    for token, (name, _, bits, kind) in zip(args, fields):
        v = reg(token) if kind == "reg" else num(token)
        ins[name] = v
        ins[name + "_p"] = fit_bits(v, bits)  # то, что реально кладём в биты
    return ins

def to_ir(text: str):
    # Этап 1: текст -> список команд (IR).
    prog = []
    for i, line in enumerate(text.splitlines(), 1):
        ins = parse_line(line, i)
        if ins:
            prog.append(ins)
    return prog

def encode_ins(ins: dict) -> bytes:
    # Этап 2: одна команда IR -> байты.
    # Собираем "одно большое число" и переводим в little-endian байты.
    A, size, fields = SPECS[ins["op"]]
    code = A  # A всегда в битах 0..3
    for name, shift, _, _ in fields:
        code |= (ins[name + "_p"] << shift)
    return code.to_bytes(size, "little", signed=False)

def encode_program(ir: list) -> bytearray:
    # Склеиваем байты всех команд подряд.
    data = bytearray()
    for ins in ir:
        data.extend(encode_ins(ins))
    return data

@click.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False))
@click.argument("out", type=click.Path(dir_okay=False))
@click.option("--test", is_flag=True, help="печатать байты по командам")
def main(src, out, test):
    text = open(src, "r", encoding="utf-8").read()

    ir = to_ir(text)
    data = encode_program(ir)

    open(out, "wb").write(data)
    click.echo(f"Размер двоичного файла: {len(data)} байт")

    # В тестовом режиме печатаем байты по командам как в спецификации.
    if test:
        for ins in ir:
            b = encode_ins(ins)
            click.echo(", ".join(f"0x{x:02X}" for x in b))

if __name__ == "__main__":
    main()
