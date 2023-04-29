from typing import Tuple

import yaml

from adafruit_servokit import ServoKit
kit = ServoKit(channels=16)

class Servo:
    """MG90D
    """
    
    def __init__(self, num: int, limits: Tuple[int, int], invert: bool=False, bias: int=0, starting_pos: int=0) -> None:
        self.num: int = num
        self.limits: Tuple[int, int] = limits
        assert(self.limits[0] < self.limits[1])
        self.invert = invert
        self.bias = -bias if self.invert else bias
        
        if (self.limits[0] < -90 + self.bias):
            self.limits = (-90 + self.bias, self.limits[1])
        if (self.limits[1] > 90 + self.bias):
            self.limits = (self.limits[0], 90 + self.bias)

        self.move(starting_pos)
    
    def move(self, pos: int) -> None:
        '''pos [-90, 90]
        '''
        if pos < self.limits[0]:
            pos = self.limits[0]
        elif pos > self.limits[1]:
            pos = self.limits[1]
        pos = -pos if self.invert else pos
        kit.servo[self.num].angle = pos - self.bias + 90
        self.pos: int = pos # [0, 180]
        print(f'Moved servo {self.num} to {self.get_pos()}')
    
    def get_pos(self) -> int:
        return -self.pos if self.invert else self.pos
    
class Gimbal:
    thread = None
    
    def __init__(self) -> None:
        with open('control/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        try:
            self.max_speed = config['gimbal']['max_speed']
            self.pan: Servo = Servo(
                num=config['gimbal']['pan_servo']['id'],
                limits=(config['gimbal']['pan_servo']['limits']['left'], config['gimbal']['pan_servo']['limits']['right']),
                invert=config['gimbal']['pan_servo']['invert'],
                bias=config['gimbal']['pan_servo']['bias']
            )
            self.tilt: Servo = Servo(
                num=config['gimbal']['tilt_servo']['id'],
                limits=(config['gimbal']['tilt_servo']['limits']['down'], config['gimbal']['tilt_servo']['limits']['up']),
                invert=config['gimbal']['tilt_servo']['invert'],
                bias=config['gimbal']['tilt_servo']['bias']
            )
        except:
            raise Exception('Gimbal init failed!')
    
    def move(self, pan_dt: int, tilt_dt: int) -> None:
        if pan_dt != 0:
            self.pan.move(self.pan.get_pos() + pan_dt)
        if tilt_dt != 0:
            self.tilt.move(self.tilt.get_pos() + tilt_dt)
