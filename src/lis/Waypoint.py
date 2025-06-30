import enum
import struct
import math

bitfield_sizes = dict()
bitfield_indexes = []

class WAYPOINT_TYPE(enum.IntEnum):
    OTHER = 0
    TAKE_OFF = 1
    GOTO = 2
    HOVER = 3
    FOLLOW = 4
    LAND = 5
    IDLE = 6
    SHUTDOWN = 7
    LOOP_BEGIN = 8
    LOOP_END = 9
bitfield_sizes[WAYPOINT_TYPE] = 4
bitfield_indexes += WAYPOINT_TYPE,

class CONTROLLER_TYPE(enum.IntEnum):
    DEFAULT = 0
    CASCATED_PID = 1
    MELLINGER = 2
    INDI = 3
    BRESCIANINI = 4
    LEE = 5
    LIS = 6
bitfield_sizes[CONTROLLER_TYPE] = 3
bitfield_indexes += CONTROLLER_TYPE,

class WAYPOINT_HL_COMMAND_TYPE(enum.IntEnum):
    VELOCITY = 0
    TIME = 1
bitfield_sizes[WAYPOINT_HL_COMMAND_TYPE] = 1
bitfield_indexes += WAYPOINT_HL_COMMAND_TYPE,
class WAYPOINT_COMMAND_TYPE(enum.IntEnum):
    HIGH_LEVEL = 0
    DIRECT = 1
bitfield_sizes[WAYPOINT_COMMAND_TYPE] = 1
bitfield_indexes += WAYPOINT_COMMAND_TYPE,
class WAYPOINT_MODE(enum.IntEnum):
    DISABLED = 0
    ABSOLUTE = 1
    VELOCITY = 2
bitfield_sizes[WAYPOINT_MODE] = 2
bitfield_indexes += WAYPOINT_MODE,
class WAYPOINT_FOLLOW_REFERENCE(enum.IntEnum):
    GLOBAL = 0
    RELATIVE = 1
bitfield_sizes[WAYPOINT_FOLLOW_REFERENCE] = 1
bitfield_indexes += WAYPOINT_FOLLOW_REFERENCE,

class WAYPOINT_POSITION_MODES:
    x: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    y: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    z: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    def copy(self):
        pm = WAYPOINT_POSITION_MODES()
        pm.x = self.x
        pm.y = self.y
        pm.z = self.z
        return pm
class WAYPOINT_ATTITUDE_MODES:
    yaw: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    pitch: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    roll: WAYPOINT_MODE = WAYPOINT_MODE.DISABLED
    def copy(self):
        am = WAYPOINT_ATTITUDE_MODES()
        am.yaw = self.yaw
        am.pitch = self.pitch
        am.roll = self.roll
        return am

class WAYPOINT_PARAMETERS:
    type: WAYPOINT_TYPE = WAYPOINT_TYPE.HOVER
    controller: CONTROLLER_TYPE = CONTROLLER_TYPE.CASCATED_PID
    command_type: WAYPOINT_COMMAND_TYPE = WAYPOINT_COMMAND_TYPE.HIGH_LEVEL
    follow_position_reference: WAYPOINT_FOLLOW_REFERENCE = WAYPOINT_FOLLOW_REFERENCE.GLOBAL
    follow_yaw_reference: WAYPOINT_FOLLOW_REFERENCE = WAYPOINT_FOLLOW_REFERENCE.GLOBAL
    hl_command_type: WAYPOINT_HL_COMMAND_TYPE = WAYPOINT_HL_COMMAND_TYPE.VELOCITY
    modes_position: WAYPOINT_POSITION_MODES
    modes_attitude: WAYPOINT_ATTITUDE_MODES

    def __init__(self):
        self.modes_position = WAYPOINT_POSITION_MODES()
        self.modes_attitude = WAYPOINT_ATTITUDE_MODES()
    def copy(self):
        p = WAYPOINT_PARAMETERS()
        p.type = self.type
        p.controller = self.controller
        p.command_type = self.command_type
        p.follow_position_reference = self.follow_position_reference
        p.follow_yaw_reference = self.follow_yaw_reference
        p.hl_command_type = self.hl_command_type
        p.modes_position = self.modes_position.copy()
        p.modes_attitude = self.modes_attitude.copy()
        return p

class WAYPOINT_POSITION_TARGET:
    x: int = 0
    y: int = 0
    z: int = 0
    def copy(self):
        pt = WAYPOINT_POSITION_TARGET()
        pt.x = self.x
        pt.y = self.y
        pt.z = self.z
        return pt
class WAYPOINT_ATTITUDE_TARGET:
    yaw: int = 0
    pitch: int = 0
    roll: int = 0
    def copy(self):
        at = WAYPOINT_ATTITUDE_TARGET()
        at.yaw = self.yaw
        at.pitch = self.pitch
        at.roll = self.roll
        return at

class Waypoint:
    parameters: WAYPOINT_PARAMETERS
    position: WAYPOINT_POSITION_TARGET
    attitude: WAYPOINT_ATTITUDE_TARGET
    loop_count: int = 1
    type_parameter: int = 0xE2
    hl_command_parameter: int = 0
    name: str = "LISwp"

    def __init__(self):
        self.modes_position = WAYPOINT_POSITION_MODES()
        self.modes_attitude = WAYPOINT_ATTITUDE_MODES()
        self.position = WAYPOINT_POSITION_TARGET()
        self.attitude = WAYPOINT_ATTITUDE_TARGET()
        self.parameters = WAYPOINT_PARAMETERS()
    def copy(self):
        wp = Waypoint()
        wp.parameters = self.parameters.copy()
        wp.attitude = self.attitude.copy()
        wp.position = self.position.copy()
        wp.loop_count = self.loop_count
        wp.type_parameter = self.type_parameter
        wp.hl_command_parameter = self.hl_command_parameter
        wp.name = self.name
        return wp

def waypoint_flag_to_bitfield(flag, bitfield_value, bitfield_index):
    bitfield_value += flag<<bitfield_index
    bitfield_index += bitfield_sizes[type(flag)]
    return bitfield_value, bitfield_index

def waypoint_flags_to_bitfield(waypoint: Waypoint):
    b = bytearray()
    bitfield_value = 0
    bitfield_index = 0
    
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.type, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.controller, bitfield_value, bitfield_index)
    bitfield_index += 1
    print(bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.follow_position_reference, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.follow_yaw_reference, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.command_type, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.hl_command_type, bitfield_value, bitfield_index)
    bitfield_index += 4
    print(bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_position.x, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_position.y, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_position.z, bitfield_value, bitfield_index)
    bitfield_index += 2
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_attitude.yaw, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_attitude.pitch, bitfield_value, bitfield_index)
    bitfield_value, bitfield_index = waypoint_flag_to_bitfield(waypoint.parameters.modes_attitude.roll, bitfield_value, bitfield_index)
    bitfield_index += 2

    bitfield_size = math.ceil(bitfield_index/8.0)
    for i in range(bitfield_size):
        v = (bitfield_value>>(i*8))&0xFF
        b += struct.pack("<B", v)
    return b

def waypoint_bitfield_to_flag(flag, bitfield, bitfield_index):
    flag_type = type(flag)
    flag = (bitfield>>bitfield_index)&bitfield_sizes[flag_type]
    bitfield_index += bitfield_sizes[flag_type]
    return flag, bitfield_index

def waypoint_bitfield_to_flags(b: bytearray, wp: Waypoint):
    bitfield = 0
    for i in range(len(b)):
        bitfield += b[i]<<(i*8)
    
    bitfield_index = 0
    wp.parameters.type, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.type, bitfield, bitfield_index)
    wp.parameters.controller, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.controller, bitfield, bitfield_index)
    wp.parameters.follow_position_reference, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.follow_position_reference, bitfield, bitfield_index)
    wp.parameters.follow_yaw_reference, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.follow_yaw_reference, bitfield, bitfield_index)
    wp.parameters.command_type, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.command_type, bitfield, bitfield_index)
    wp.parameters.hl_command_type, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.hl_command_type, bitfield, bitfield_index)
    wp.parameters.modes_position.x, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_position.x, bitfield, bitfield_index)
    wp.parameters.modes_position.y, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_position.y, bitfield, bitfield_index)
    wp.parameters.modes_position.z, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_position.z, bitfield, bitfield_index)
    wp.parameters.modes_attitude.yaw, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_attitude.yaw, bitfield, bitfield_index)
    wp.parameters.modes_attitude.pitch, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_attitude.pitch, bitfield, bitfield_index)
    wp.parameters.modes_attitude.roll, bitfield_index = waypoint_bitfield_to_flag(wp.parameters.modes_attitude.roll, bitfield, bitfield_index)
    wp.parameters.type = WAYPOINT_TYPE(wp.parameters.type)
    wp.parameters.controller = CONTROLLER_TYPE(wp.parameters.controller)
    wp.parameters.command_type = WAYPOINT_COMMAND_TYPE(wp.parameters.command_type)
    wp.parameters.follow_position_reference = WAYPOINT_FOLLOW_REFERENCE(wp.parameters.follow_position_reference)
    wp.parameters.follow_yaw_reference = WAYPOINT_FOLLOW_REFERENCE(wp.parameters.follow_yaw_reference)
    wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE(wp.parameters.hl_command_type)
    wp.parameters.modes_position.x = WAYPOINT_MODE(wp.parameters.modes_position.x)
    wp.parameters.modes_position.y = WAYPOINT_MODE(wp.parameters.modes_position.y)
    wp.parameters.modes_position.z = WAYPOINT_MODE(wp.parameters.modes_position.z)
    wp.parameters.modes_attitude.yaw = WAYPOINT_MODE(wp.parameters.modes_attitude.yaw)
    wp.parameters.modes_attitude.pitch = WAYPOINT_MODE(wp.parameters.modes_attitude.pitch)
    wp.parameters.modes_attitude.roll = WAYPOINT_MODE(wp.parameters.modes_attitude.roll)

def waypoint_to_bytes(waypoint: Waypoint):
    b = bytearray()
    b += waypoint_flags_to_bitfield(waypoint)
    b += struct.pack(
        "<6hBhh",
        waypoint.position.x,
        waypoint.position.y,
        waypoint.position.z,
        waypoint.attitude.yaw,
        waypoint.attitude.pitch,
        waypoint.attitude.roll,
        waypoint.loop_count,
        waypoint.type_parameter,
        waypoint.hl_command_parameter)
    return b

def bytes_to_waypoint(b: bytearray):
    waypoint = Waypoint()
    waypoint_bitfield_to_flags(b, waypoint)
    b.pop(0)
    b.pop(0)
    b.pop(0)
    b.pop(0)
    waypoint.position.x, \
    waypoint.position.y, \
    waypoint.position.z, \
    waypoint.attitude.yaw, \
    waypoint.attitude.pitch, \
    waypoint.attitude.roll, \
    waypoint.loop_count, \
    waypoint.type_parameter, \
    waypoint.hl_command_parameter = struct.unpack("<6hBhh", b)
    return waypoint

if __name__=="__main__":
    wp1 = Waypoint()
    wp1.parameters.type = WAYPOINT_TYPE.HOVER
    wp1.parameters.controller = CONTROLLER_TYPE.CASCATED_PID
    wp1.parameters.follow_position_reference = WAYPOINT_FOLLOW_REFERENCE.RELATIVE
    wp1.parameters.follow_attitude_reference = WAYPOINT_FOLLOW_REFERENCE.RELATIVE
    b = waypoint_to_bytes(wp1)
    print("\\".join(hex(h) for h in b))
    # print("")
    # wp2 = bytes_to_waypoint(b)
    # print(waypoint_to_bytes(wp2))
