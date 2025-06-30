import struct
import enum

from lis import Waypoint

class GS_PACKET_TYPE(enum.IntEnum):
    GS_PACKET_TYPE_PING = 0,
    GS_PACKET_TYPE_COMMAND = 1,
    GS_PACKET_TYPE_STOP = 2,
    GS_PACKET_TYPE_STRING = 3,
    GS_PACKET_TYPE_P2P_SYSTEM = 4,
    GS_PACKET_TYPE_POLL = 5,
    GS_PACKET_TYPE_POLL_RESPONSE = 6,

class GS_PACKET_POLL_PACKET:
    state: int = 0
    is_leader: int = 0
    x: int = 0
    y: int = 0
    z: int = 0
    yaw: int = 0
    pitch: int = 0
    roll: int = 0

class GS_PACKET_DATA:
    waypoint: Waypoint
    string: str

class GS_Packet:
    type: GS_PACKET_TYPE = GS_PACKET_TYPE.GS_PACKET_TYPE_POLL
    receiver_address: int = 0xFF
    data: GS_PACKET_DATA
    def __init__(self):
        self.data = GS_PACKET_DATA()

def gs_packet_to_bytes(packet: GS_Packet):
    b = bytearray()
    b += struct.pack("<BB", packet.type, packet.receiver_address)
    if packet.type==GS_PACKET_TYPE.GS_PACKET_TYPE_STRING:
        b += packet.data.string.encode('utf-8')
    if packet.type==GS_PACKET_TYPE.GS_PACKET_TYPE_COMMAND:
        b += Waypoint.waypoint_to_bytes(packet.data.waypoint)
    return b

def create_p2p_packet(p2p_address, pkt_bytes):
    return pkt_bytes

def bytes_to_poll_packet(data: bytearray):
    poll_packet = GS_PACKET_POLL_PACKET()
    poll_packet.state, \
    poll_packet.is_leader, \
    poll_packet.x, \
    poll_packet.y, \
    poll_packet.z, \
    poll_packet.yaw, \
    poll_packet.pitch, \
    poll_packet.roll = struct.unpack("<BBhhhhhh", data)
    return poll_packet