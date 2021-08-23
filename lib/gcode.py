from typing import TextIO, Generator


def readGcodeLine(line: str) -> Generator[tuple[str, float], None, None]:
    for token in line.strip().split(' '):
        command, value = token[0], float(token[1:])
        assert command.isalpha(), f'Invalid command name: {command}'
        yield command, value


def writeGcodeLine(file: TextIO, commands: dict[str, float]):
    file.write(' '.join(f'{command}{value}' for command, value in commands))
