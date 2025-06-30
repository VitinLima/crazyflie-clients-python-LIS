import os
import time
import csv
import threading

from PyQt6.QtCore import pyqtSignal, QTimer, QObject

from cflib.crazyflie.log import LogConfig
import cflib.crazyflie as Crazyflie

from lis import Waypoint, Protocol

import numpy as np
_silent = False

default_log_configs = {
    'log_stateEstimatePos': dict(
        key='log_stateEstimatePos',
        name='State estimate position', period_in_ms=50,
        variables={
            'stateEstimate.x':'float',
            'stateEstimate.y':'float',
            'stateEstimate.z':'float',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_stateEstimateVel': dict(
        key='log_stateEstimateVel',
        name='State estimate velocity', period_in_ms=50,
        variables={
            'stateEstimate.vx':'float',
            'stateEstimate.vy':'float',
            'stateEstimate.vz':'float',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_stateEstimateAcc': dict(
        key='log_stateEstimateAcc',
        name='State estimate acceleration', period_in_ms=50,
        variables={
            'stateEstimate.ax':'float',
            'stateEstimate.ay':'float',
            'stateEstimate.az':'float',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_stateEstimateAtt': dict(
        key='log_stateEstimateAtt',
        name='State estimate attitude', period_in_ms=50,
        variables={
            'stateEstimate.yaw':'float',
            'stateEstimate.pitch':'float',
            'stateEstimate.roll':'float',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_stateEstimateAttRate': dict(
        key='log_stateEstimateAttRate',
        name='State estimate attitude rate', period_in_ms=50,
        variables={
            'stateEstimateZ.rateYaw':'int16_t',
            'stateEstimateZ.ratePitch':'int16_t',
            'stateEstimateZ.rateRoll':'int16_t',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_ctrltargetZPosVelAcc': dict(
        key='log_ctrltargetZPos',
        name='Desired position, vel and accel, compressed', period_in_ms=50,
        variables={
            'ctrltargetZ.x':'int16_t',
            'ctrltargetZ.y':'int16_t',
            'ctrltargetZ.z':'int16_t',
            'ctrltargetZ.vx':'int16_t',
            'ctrltargetZ.vy':'int16_t',
            'ctrltargetZ.vz':'int16_t',
            'ctrltargetZ.ax':'int16_t',
            'ctrltargetZ.ay':'int16_t',
            'ctrltargetZ.az':'int16_t',
            },
        callbacks=[],
        logdata=[],
        ),
    'log_ctrltargetAtt': dict(
        key='log_ctrltargetAtt',
        name='Desired pitch and roll angles, and yaw rate', period_in_ms=50,
        variables={
            'ctrltarget.yaw':'float',
            'ctrltarget.pitch':'float',
            'ctrltarget.roll':'float',
            },
        callbacks=[],
        logdata=[],
        ),
    }

class Backend(QObject):
    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)
    _appchannel_received_signal = pyqtSignal(bytearray)

    def __init__(self):
        super().__init__()
        self.cf = None

        self.logs = []
        self.N_readings = 200
        self.readings = np.zeros((8,self.N_readings))
        self.readings_indexes = [0,0,0,0,0,0,0,0]
        self.is_measuring = False
        self.is_connected = False
        self.offsets = 20*np.ones((8,))
        self.offsets_log = []
        for i in range(8):
            self.offsets_log += [20*np.ones((200,))]
        # self.timer = QTimer(parent=None, timeout=self.poll)

        self.running_logs = []
        self.is_p2p_system = False
        self.p2p_address = 0xE2

        self.poll_callbacks = []
        self.polling_timer = QTimer(parent=self)
        self.polling_timer.setInterval(500)
        self.polling_timer.timeout.connect(self.on_poll)
    
    def add_poll_callback(self, callback):
        self.poll_callbacks.append(callback)
    
    def add_callback_to_log(self, log_key: str, callback):
        if log_key in default_log_configs:
            default_log_configs[log_key]['callbacks'] += [callback]
    
    def on_start(self):
        if self.is_p2p_system:
            self.send_message('start', p2p_address=self.p2p_address)
        else:
            self.send_message('start')

    def on_land(self):
        if self.is_p2p_system:
            self.send_message('land', p2p_address=self.p2p_address)
        else:
            self.send_message('land')

    def on_emergency_stop(self):
        if self.is_p2p_system:
            self.send_message('stop', p2p_address=self.p2p_address)
        else:
            self.send_message('stop')

    def on_system_reset(self):
        if self.is_p2p_system:
            self.send_message('reset', p2p_address=self.p2p_address)
            self.stop_logs()
        else:
            self.send_message('reset')
            self.stop_logs()

    def on_unlock(self):
        if self.is_p2p_system:
            self.send_message('unlock', p2p_address=self.p2p_address)
        else:
            self.send_message('unlock')

    def on_greetings(self):
        packet = Protocol.GS_Packet()
        packet.type = Protocol.GS_PACKET_TYPE.GS_PACKET_TYPE_PING
        if self.is_p2p_system:
            self.send_packet(packet, p2p_address=self.p2p_address)
        else:
            self.send_packet(packet)
    
    def on_take_leader(self):
        if self.is_p2p_system:
            self.send_message('take leader', p2p_address=self.p2p_address)
        else:
            self.send_message('take leader')
    
    def send_waypoint(self, waypoint: Waypoint):
        packet = Protocol.GS_Packet()
        packet.type = Protocol.GS_PACKET_TYPE.GS_PACKET_TYPE_COMMAND
        packet.data.waypoint = waypoint
        if self.is_p2p_system:
            self.send_packet(packet, p2p_address=self.p2p_address)
        else:
            self.send_packet(packet)
    
    def send_message(self, message: str, silent=_silent, p2p_address=None):
        if self.is_connected:
            packet = Protocol.GS_Packet()
            packet.type = Protocol.GS_PACKET_TYPE.GS_PACKET_TYPE_STRING
            packet.data.string = message
            self.send_packet(packet, silent=silent, p2p_address=p2p_address)
    
    def send_packet(self, packet: Protocol.GS_Packet, silent=_silent, p2p_address=None):
        if self.is_connected:
            if self.is_p2p_system:
                packet.receiver_address = self.p2p_address
            else:
                if p2p_address is None:
                    packet.receiver_address = 0xFF
                else:
                    packet.receiver_address = p2p_address
            pkt_bytes = Protocol.gs_packet_to_bytes(packet)
            self.cf.appchannel.send_packet(pkt_bytes)
            if not silent:
                print(pkt_bytes)
    
    def attach_cf(self, cf: Crazyflie):
        self.cf = cf

        self.cf.connected.add_callback(self._connected_signal.emit)
        self.cf.disconnected.add_callback(self._disconnected_signal.emit)
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)

        self.cf.appchannel.packet_received.add_callback(self._appchannel_received_signal.emit)
        self._appchannel_received_signal.connect(self._app_packet_received)
        # self.cf.console.receivedChar.add_callback(self.console_received)
    
    def on_poll(self, p2p_target=None):
        packet = Protocol.GS_Packet()
        packet.type = Protocol.GS_PACKET_TYPE.GS_PACKET_TYPE_POLL
        if self.is_p2p_system:
            self.send_packet(packet, silent=True, p2p_address=self.p2p_address)
        else:
            self.send_packet(packet, silent=True)

    def set_p2p_system(self, is_p2p_system):
        self.is_p2p_system=is_p2p_system
    
    def set_p2p_address(self, p2p_address):
        self.p2p_address=p2p_address

    # def search_available_connections(self, addresses_list):
    #     # available_addresses = [("radio", "")]
    #     available_addresses = []
    #     for address in addresses_list:
    #         available_addresses += cflib.crtp.scan_interfaces(address)
    #     return available_addresses
    
    def start_measuring(self, reference):
        if self.is_connected:
            self.reference = reference
            self.readings = np.zeros((8,self.N_readings))
            self.readings_indexes = [0,0,0,0,0,0,0,0]
            self.is_measuring = True
        else:
            # t = threading.Thread(target=self.simulate_data_collection)
            # t.start()
            return
    
    def start_logs(self):
        newlogs = []
        for log in default_log_configs.values():
            newlog = LogConfig(name=log['name'],period_in_ms=log['period_in_ms'])
            for key in log['variables'].keys():
                newlog.add_variable(key, log['variables'][key])
            for callback in log['callbacks']:
                newlog.data_received_cb.add_callback(callback)
            newlogs += [newlog]
        for newlog in newlogs:
            self.running_logs += [newlog]
            self.cf.log.add_config(newlog)
            newlog.start()
    
    def start_new_log(self, newlog):
        self.running_logs += [newlog]
        self._helper.cf.log.add_config(newlog)
        newlog.start()

    def stop_logs(self):
        for log in self.running_logs:
            if log.started:
                log.stop()
    
    def simulate_data_collection(self):
        sqrt_var = np.sqrt(0.1)
        for log in self.logs:
            variable_id = "ranging.distance{}".format(log.name)
            data = {}
            mean_dist = np.random.rand()*3
            for j in range(self.N_readings):
                data[variable_id] = np.random.randn()*sqrt_var+mean_dist
                self.callback_ranging_distance(0, data, log)
                # time.sleep(0.001)

    def callback_ranging_distance(self, timestamp, data, logconf):
        anchor_id = int(logconf.name)
        variable_id = 'ranging.distance{}'.format(anchor_id)
        reading = data[variable_id]
        reading_id = self.readings_indexes[anchor_id]

        self.offsets_log[anchor_id][0] = reading
        self.offsets_log[anchor_id] = np.roll(self.offsets_log[anchor_id], 1)
        offset_log_mean = np.mean(self.offsets_log[anchor_id])
        if offset_log_mean < self.offsets[anchor_id]:
            self.offsets[anchor_id] = offset_log_mean
            # self.app.offset_frame.update_offset(anchor_id, offset_log_mean)

        if self.is_measuring and reading_id<self.N_readings:
            self.readings[anchor_id,reading_id] = reading
            self.reference.tkvar_x.set("{:.2f}".format(reading))

            mean = np.mean(self.readings[anchor_id,0:reading_id+1])
            var = np.var(self.readings[anchor_id,0:reading_id+1])

            reading_id = reading_id+1
            self.readings_indexes[anchor_id] = reading_id
            self.reference.update_anchor_progress(anchor_id, reading_id/self.N_readings*100, mean, var)
    
    def _app_packet_received(self, data):
        # print("App channel received: ")
        # print(len(data))
        if data[0]==Protocol.GS_PACKET_TYPE.GS_PACKET_TYPE_POLL_RESPONSE:
            polling_data = Protocol.bytes_to_poll_packet(data[2:])
            for callback in self.poll_callbacks:
                callback(polling_data)
    
    def console_received(self, data):
        print(data, end='')

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        # print("Connection to %s succeeded" % link_uri)
        self.is_connected = True
        self.start_logs()
        self.polling_timer.start()

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        # print('Disconnected from %s' % link_uri)
        self.is_connected = False
        self.polling_timer.stop()
        self.stop_logs()
    
    def update(self):
        if self.is_measuring:
            for i in self.readings_indexes:
                if i != self.N_readings:
                    return
            
            self.is_measuring = False
            self.reference.readings_completed_cb(self.readings)