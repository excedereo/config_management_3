; кладём значения в память 500..502
LOAD_CONST r1, 40
STORE_MEM 500, r1
LOAD_CONST r1, 50
STORE_MEM 501, r1
LOAD_CONST r1, 60
STORE_MEM 502, r1

; левый операнд в регистре r2
LOAD_CONST r2, 50

; сравнения и сохранение результата
CMP_GE r3, r2, 500
STORE_MEM 600, r3

CMP_GE r3, r2, 501
STORE_MEM 601, r3

CMP_GE r3, r2, 502
STORE_MEM 602, r3
