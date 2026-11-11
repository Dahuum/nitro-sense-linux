"""Pure encoders recovered from NitroSense 3.1.3056.0, without hardware I/O.

These encode the *Windows application's input words*. They do not identify Linux
WMI method IDs or establish that a command works on a particular keyboard.
See docs/protocol-evidence.md for artifact identity and exact source methods.
Input validation is a reconstruction design choice; packing is recovered.
"""
from enum import IntEnum


class Pattern(IntEnum):
    BREATHING = 0
    WAVE = 1
    ZOOM = 2
    SHIFTING = 3
    NEON = 4


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in {low}..{high}')
    return value


def fan_mode(mode: str) -> int:
    """CommonFunction.set_all_fan_mode; service command 15."""
    return 9 | {'auto': 0x410000, 'max': 0x820000, 'custom': 0xC30000}[mode]


def fan_behavior(cpu_auto: bool, gpu_auto: bool) -> int:
    """CommonFunction.set_all_custom_fan_state's behavior word."""
    if type(cpu_auto) is not bool or type(gpu_auto) is not bool:
        raise ValueError('automatic flags must be booleans')
    return 9 | ((1 if cpu_auto else 3) << 16) | ((1 if gpu_auto else 3) << 22)


def fan_speed(group: str, percentage: int) -> int:
    """CommonFunction.set_single_custom_fan_speed; service command 16."""
    return {'cpu': 1, 'gpu': 4}[group] | (_integer(percentage, 0, 100, 'percentage') << 8)


def coolboost(enabled: bool) -> int:
    """CommonFunction.set_coolboost_state; service command 17."""
    if type(enabled) is not bool:
        raise ValueError('enabled must be boolean')
    return 7 | (int(enabled) << 16)


def zone_rgb(zone: int, red: int, green: int, blue: int) -> int:
    """Popup_Lighting.Change_Zone_Color; service command 28.

    Channels are already adjusted/brightness-scaled. AN515-45 packaged channel
    adjustment factors are each 1.0. Channel adjustment is not performed here.
    """
    _integer(zone, 1, 4, 'zone')
    for name, value in [('red', red), ('green', green), ('blue', blue)]:
        _integer(value, 0, 255, name)
    return (1 << (zone - 1)) | (red << 8) | (green << 16) | (blue << 24)


def zone_status(enabled: tuple[bool, bool, bool, bool]) -> int:
    """Popup_Lighting.Change_Zone_Status; service command 29."""
    if len(enabled) != 4 or any(type(value) is not bool for value in enabled):
        raise ValueError('four boolean zone states required')
    return 8 | sum(int(value) << (40 + index) for index, value in enumerate(enabled))


def dynamic_lighting(pattern: Pattern, speed: int, brightness_step: int,
                     direction: int, red: int, green: int, blue: int) -> int:
    """LightingDynamicUI.Set_Dynamic_Keyboard; service command 27.

    Brightness steps 1..5 map to 0,25,50,75,100. Direction is a raw byte:
    the supported values differ by effect. Colors are already adjusted.
    """
    pattern = Pattern(pattern)
    _integer(speed, 0, 255, 'speed')
    _integer(brightness_step, 1, 5, 'brightness_step')
    _integer(direction, 0, 255, 'direction')
    for name, value in [('red', red), ('green', green), ('blue', blue)]:
        _integer(value, 0, 255, name)
    effect_id = {Pattern.BREATHING: 1, Pattern.NEON: 2, Pattern.WAVE: 3,
                 Pattern.SHIFTING: 4, Pattern.ZOOM: 5}[pattern]
    word = effect_id | (speed << 8) | (((brightness_step - 1) * 25) << 16)
    if pattern in (Pattern.WAVE, Pattern.SHIFTING):
        word |= direction << 32
    if pattern == Pattern.WAVE:
        word |= 0x08000000
    if pattern != Pattern.NEON:
        word |= (red << 40) | (green << 48) | (blue << 56)
    return word


def service_u64_request(command: int, word: int) -> bytes:
    """TsDotNetLib.IPCMethods framing for exactly one Windows UInt64 argument.

    Deliberately a byte encoder only. It neither connects to the Acer service
    nor makes its Windows command number a Linux WMI method number.
    """
    import struct
    _integer(command, 0, 65535, 'command')
    _integer(word, 0, (1 << 64) - 1, 'word')
    return struct.pack('<HBIQ', command, 1, 8, word)
