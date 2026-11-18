from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from src.config import (
    DOOR_ACTIVE_S,
    DOOR_HEIGHT,
    DOOR_REACH,
    DOOR_SITE_M,
    DOOR_WARNING_DISTANCE_M,
    DOOR_WARNING_S,
    PARKED_CAR_LENGTH,
    PARKED_CAR_WIDTH,
    RIDER_SCREEN_Y,
    ROAD_CENTER_X,
    ROAD_SCALE_PX_PER_M,
    ROAD_WIDTH,
)


class DoorPhase(Enum):
    WAITING = auto()
    WARNING = auto()
    OPEN = auto()
    CLOSED = auto()


@dataclass
class DoorHazard:
    distance_m: float = DOOR_SITE_M
    _elapsed_s: float | None = field(default=None, init=False)

    @property
    def phase(self) -> DoorPhase:
        if self._elapsed_s is None:
            return DoorPhase.WAITING
        if self._elapsed_s < DOOR_WARNING_S:
            return DoorPhase.WARNING
        if self._elapsed_s < DOOR_WARNING_S + DOOR_ACTIVE_S:
            return DoorPhase.OPEN
        return DoorPhase.CLOSED

    def update(self, dt: float, rider_distance_m: float) -> None:
        if self._elapsed_s is not None:
            self._elapsed_s = min(self._elapsed_s + dt, DOOR_WARNING_S + DOOR_ACTIVE_S)
        elif self.distance_m - rider_distance_m <= DOOR_WARNING_DISTANCE_M:
            self._elapsed_s = 0.0

    def car_bounds(self, rider_distance_m: float) -> pygame.FRect:
        car_left = ROAD_CENTER_X + ROAD_WIDTH / 2
        door_y = RIDER_SCREEN_Y + (rider_distance_m - self.distance_m) * ROAD_SCALE_PX_PER_M
        return pygame.FRect(car_left, door_y - DOOR_HEIGHT, PARKED_CAR_WIDTH, PARKED_CAR_LENGTH)

    def door_bounds(self, rider_distance_m: float) -> pygame.FRect:
        car = self.car_bounds(rider_distance_m)
        return pygame.FRect(car.left - DOOR_REACH, car.top + DOOR_HEIGHT / 2, DOOR_REACH, DOOR_HEIGHT)
