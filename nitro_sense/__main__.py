"""Native desktop entry point. Opening the app never changes hardware settings."""
import argparse
import json
import os
import sys
from .backend import Backend

VERSION = '0.2.0'


def main():
    parser = argparse.ArgumentParser(description='NitroSense Linux — native Acer AN515-45 controls')
    parser.add_argument('--version', action='version', version=f'NitroSense Linux {VERSION}')
    parser.add_argument('--diagnose', action='store_true', help='Print actual local telemetry and capabilities without changing settings')
    parser.add_argument('--enable-control', action='store_true', help='Allow explicit user actions through already writable compatible interfaces (default)')
    parser.add_argument('--read-only', action='store_true', help='Disable hardware and power-profile changes')
    parser.add_argument('--smoke-test', action='store_true', help='Render the native UI briefly and exit without hardware writes')
    parser.add_argument('--screenshot', help='Output PNG path for --smoke-test')
    args = parser.parse_args()
    if args.screenshot:
        os.environ['NITRO_SENSE_SCREENSHOT'] = args.screenshot
    backend = Backend(allow_control=not args.read_only and not args.smoke_test)
    try:
        if args.diagnose:
            print(json.dumps(backend.snapshot(), indent=2))
            return 0
        from .ui import run
        return run(backend=backend, smoke_test=args.smoke_test)
    finally:
        # A second close is harmless, and covers import/setup failures as well as
        # exceptions outside the normal Qt window-close path.
        backend.close()


if __name__ == '__main__':
    sys.exit(main())
