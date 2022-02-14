from typing import TextIO, Generator


def read_gcode_line(line: str) -> Generator[tuple[str, float], None, None]:
    for token in line.strip().split(' '):
        if token == '':
            continue
        if token[0] == '#':
            break
        command, value = token[0], float(token[1:])
        assert command.isalpha(), f'Invalid command name: {command}'
        yield command, value


def write_gcode_line(file: TextIO, commands: dict[str, float]):
    file.write(' '.join(f'{command}{value}' for command, value in commands))
