from typing import Tuple, Optional
import yaml
import numpy as np
import time
from operator import sub
from threading import Thread

from adafruit_servokit import ServoKit as afServoKit
from adafruit_motor.servo import Servo as afServo

class Servo:
    """MG90D
    """
    
    def __init__(self, af_servo: afServo, limits: Tuple[int, int], invert: bool=False, bias: int=0, starting_pos: int=0) -> None:
        self.af_servo: afServo = af_servo
        self.limits: Tuple[int, int] = limits
        assert(self.limits[0] < self.limits[1])
        self.invert = invert
        self.bias = -bias if self.invert else bias
        
        self.limits = tuple(np.clip(l, -90 + self.bias, 90 + self.bias) for l in self.limits)

        print(f'Starting pos: {self.af_servo.angle}')
        self.move(starting_pos)
    
    def __del__(self) -> None:
        # disable the servo
        # TODO: ctrl+c'ing in terminal causes an exception here because Python is already too far shutdown
        #       need to catch singal
        self.af_servo.angle = None
    
    def move(self, pos: int) -> None:
        '''Accepts commands in range [-90, 90] deg'''
        if pos < self.limits[0]:
            pos = self.limits[0]
        elif pos > self.limits[1]:
            pos = self.limits[1]
        pos = -pos if self.invert else pos
        self.af_servo.angle = pos - self.bias + 90
        self.pos: int = pos # [0, 180]
    
    def get_pos(self) -> int:
        '''Returns position in range [-90, 90] deg'''
        return -self.pos if self.invert else self.pos
    
class Gimbal:
    thread = None
    af_servo_kit: afServoKit = afServoKit(channels=16)
    target_pos: Tuple[int, int] = (0, 0) # Pan Tilt target
    cmd_pos: Tuple[float, float] = (0, 0) # Used for smooth movement
    update_period_ns: int = 20000000 # 50hz (from servo duty cycle)
    max_speed: float = 2 # deg/s
    pan: Optional[Servo] = None
    tilt: Optional[Servo] = None

    def __init__(self) -> None:
        if Gimbal.thread is None:
            # TODO: fix pathing
            with open('control/config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            try:
                # TODO: validate yaml contents
                Gimbal.max_speed = config['gimbal']['max_speed']
                Gimbal.pan = Servo(
                    af_servo=Gimbal.af_servo_kit.servo[config['gimbal']['pan_servo']['id']],
                    limits=(config['gimbal']['pan_servo']['limits']['left'], config['gimbal']['pan_servo']['limits']['right']),
                    invert=config['gimbal']['pan_servo']['invert'],
                    bias=config['gimbal']['pan_servo']['bias']
                )
                Gimbal.tilt = Servo(
                    af_servo=Gimbal.af_servo_kit.servo[config['gimbal']['tilt_servo']['id']],
                    limits=(config['gimbal']['tilt_servo']['limits']['down'], config['gimbal']['tilt_servo']['limits']['up']),
                    invert=config['gimbal']['tilt_servo']['invert'],
                    bias=config['gimbal']['tilt_servo']['bias']
                )
                print("set config")
            except:
                raise Exception('Gimbal init failed!')
            else:
                print("starting thread")
                Gimbal.thread = Thread(target=self._thread)
                Gimbal.thread.start()

    def move(self, target_pos: Tuple[int, int]) -> None:
        '''target_dt: (pan_deg_dt, tilt_deg_dt)'''
        Gimbal.target_pos = tuple(np.clip(t, -90, 90) for t in target_pos)
        print(Gimbal.target_pos)
    
    def move_relative(self, target_dt: Tuple[int, int]) -> None:
        '''target_dt: (pan_deg_dt, tilt_deg_dt)'''
        self.move((
            target_dt[0] + Gimbal.target_pos[0],
            target_dt[1] + Gimbal.target_pos[1],
        ))

    @classmethod
    def _thread(cls):
        print("\nStarting Gimbal Thread!\n")
        dt_s = Gimbal.max_speed * (Gimbal.update_period_ns / 1e9)
        while True:
            # For now, always move at max speed
            pos_dt = tuple(map(sub, Gimbal.target_pos, Gimbal.cmd_pos))
            Gimbal.cmd_pos = tuple(c + p * dt_s for c, p in zip(Gimbal.cmd_pos, pos_dt))

            if Gimbal.pan:
                Gimbal.pan.move(int(Gimbal.cmd_pos[0]))
            if Gimbal.tilt:
                Gimbal.tilt.move(int(Gimbal.cmd_pos[1]))
            
            # this assumes while loop contents have a max execution time < Gimbal.update_period
            time.sleep((time.monotonic_ns() % Gimbal.update_period_ns) / 1e9)
        