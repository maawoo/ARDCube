from ARDCube.download_level1 import download_level1
from ARDCube.generate_ard import generate_ard
from ARDCube.prepare_odc import prepare_odc

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
    elif command in ['generate', 'process']:
        generate_ard(sensor=sensor,
                     debug_force=False)
    elif command == 'prepare':
        prepare_odc(sensor=sensor,
                    overwrite=True)
    else:
        raise ValueError(f"Command '{command}' not recognized.")


if __name__ == '__main__':
    main()
