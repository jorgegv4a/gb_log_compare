import re
from collections import deque
from pathlib import Path

from general import txt


def main():
    # Path to the log under test
    testing_log = Path("mojo.log")

    # Path to the ground truth log
    correct_log = Path("rust.log")

    with open(testing_log) as f:
        test_lines = f.readlines()

    for i, line in enumerate(test_lines):
        if re.match("AF: ", line) is not None:
            test_lines = test_lines[i:]
            break

    with open(correct_log) as f:
        correct_lines = f.readlines()
    for i, line in enumerate(correct_lines):
        if re.match("AF: ", line) is not None:
            correct_lines = correct_lines[i:]
            break

    out_lines = deque(maxlen=10)

    stop = False
    for i, items in enumerate(zip(correct_lines[::2], test_lines[::2])):
        data = []
        for item in items:
            data.append(parse_cpu_status(item))

        msg = []
        for j, (ok_val, test_val) in enumerate(zip(*data)):
            if ok_val == test_val:
                msg.append(txt(f"%g  {test_val}"))
            else:
                msg.append(txt(f"%rku{test_val}"))
                if j != 11:
                    stop = True

        line = f"AF: {msg[0]}, BC: {msg[1]}, DE: {msg[2]}, HL: {msg[3]}, SP: {msg[4]}, PC: {msg[5]}, F: {msg[6]}{msg[7]}{msg[8]}{msg[9]} | IME: {msg[10]} | T: {msg[11]}"
        out_lines.append(line)
        if stop:
            msg = [txt(f"%g  {x}") for x in data[0]]
            line = f"AF: {msg[0]}, BC: {msg[1]}, DE: {msg[2]}, HL: {msg[3]}, SP: {msg[4]}, PC: {msg[5]}, F: {msg[6]}{msg[7]}{msg[8]}{msg[9]} | IME: {msg[10]} | T: {msg[11]}"
            out_lines.append(line)
            break
        out_lines.append("\n" + txt(f"%y  {test_lines[i * 2 + 1].strip()}"))
    [print(x) for x in out_lines]


def parse_cpu_status(line):
    match = re.match(r"AF: ([\dA-F]{4}), BC: ([\dA-F]{4}), DE: ([\dA-F]{4}), HL: ([\dA-F]{4}), SP: ([\dA-F]{4}), PC: ([\dA-F]{4}), F: (Z|-)(N|-)(H|-)(C|-) \| IME: (\d) \| T: (\d+)", line)
    AF, BC, DE, HL, SP, PC, FZ, FN, FH, FC, IME, T = match.groups()
    return AF, BC, DE, HL, SP, PC, FZ, FN, FH, FC, IME, T


if __name__ == '__main__':
    main()
