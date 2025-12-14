import click

SPECS = {
    "LC":  (0, 4, [("B", 4, 7, "reg"), ("C", 11, 20, "imm")]),
    "LDM": (13, 5, [("B", 4, 15, "imm"), ("C", 19, 7, "reg"), ("D", 26, 7, "reg")]),
    "STM": (9, 3, [("B", 4, 10, "imm"), ("C", 14, 7, "reg")]),
    "GE":  (15, 4, [("B", 4, 7, "reg"), ("C", 11, 10, "imm"), ("D", 21, 7, "reg")]),
}

ALIASES = {
    "LOAD_CONST": "LC", "LC": "LC",
    "LOAD_MEM": "LDM",  "LDM": "LDM",
    "STORE_MEM": "STM", "STM": "STM",
    "CMP_GE": "GE",     "GE": "GE",
}

def clean(s: str) -> str:
    return s.split(";", 1)[0].split("#", 1)[0].strip()

def num(t: str) -> int:
    return int(t, 0)

def reg(t: str) -> int:
    t = t.strip()
    if t[:1].lower() == "r":
        t = t[1:]
    return num(t)

def fit_bits(x: int, bits: int) -> int:
    if x < 0:
        x = (1 << bits) + x
    if not (0 <= x < (1 << bits)):
        raise ValueError(f"{x} не влезает в {bits} бит")
    return x

def parse_line(line: str, n: int):
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

    # Понятный синтаксис:
    # LOAD_MEM rC, rD, B
    # CMP_GE   rD, rB, C
    if op == "LDM":
        if len(args) != 3: raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[2], args[0], args[1]]  # -> B, C, D
    if op == "GE":
        if len(args) != 3: raise ValueError(f"строка {n}: неверно аргументов")
        args = [args[1], args[2], args[0]]  # -> B, C, D

    if len(args) != len(fields):
        raise ValueError(f"строка {n}: неверно аргументов")

    ins = {"op": op, "A": A}
    for token, (name, _, bits, kind) in zip(args, fields):
        v = reg(token) if kind == "reg" else num(token)
        ins[name] = v
        ins[name + "_p"] = fit_bits(v, bits)
    return ins

def to_ir(text: str):
    prog = []
    for i, line in enumerate(text.splitlines(), 1):
        ins = parse_line(line, i)
        if ins:
            prog.append(ins)
    return prog

def encode_ins(ins: dict) -> bytes:
    A, size, fields = SPECS[ins["op"]]
    code = A
    for name, shift, _, _ in fields:
        code |= (ins[name + "_p"] << shift)
    return code.to_bytes(size, "little", signed=False)

def encode_program(ir: list) -> bytearray:
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

    if test:
        for ins in ir:
            b = encode_ins(ins)
            click.echo(", ".join(f"0x{x:02X}" for x in b))

if __name__ == "__main__":
    main()
