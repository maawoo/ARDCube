from ARDCube.download_level1 import download_level1
from ARDCube.generate_ard import generate_ard

import sys


def main():
    # Optional params?
    # Print help when only 'help' is given as command?

    command = sys.argv[1]
    sensor = sys.argv[2]
    sensor = sensor.lower()  # Make lowercase

    if command == 'download':
        download_level1(sensor=sensor,
                        debug_force=False)
    elif command == 'generate':
        generate_ard(sensor=sensor,
                     debug_force=False)
    else:
        raise ValueError(f"Command '{command}' not recognized.")


if __name__ == '__main__':
    main()
