from dataclasses import dataclass

from src.config import (
    ACCELERATION_MPS2,
    BRAKE_MPS2,
    LATERAL_SPEED_PXPS,
    MAX_SPEED_MPS,
    RIDER_MAX_X,
    RIDER_MIN_X,
    ROAD_CENTER_X,
    START_SPEED_MPS,
)


@dataclass
class Player:
    x: float = ROAD_CENTER_X
    speed_mps: float = START_SPEED_MPS
    distance_m: float = 0.0

    def update(self, dt: float, steering: int, accelerate: bool, brake: bool) -> None:
        acceleration = 0.0
        if brake:
            acceleration = -BRAKE_MPS2
        elif accelerate:
            acceleration = ACCELERATION_MPS2

        acceleration_seconds = dt
        if acceleration > 0:
            acceleration_seconds = min(dt, (MAX_SPEED_MPS - self.speed_mps) / acceleration)
        elif acceleration < 0:
            acceleration_seconds = min(dt, self.speed_mps / -acceleration)

        next_speed = min(MAX_SPEED_MPS, max(0.0, self.speed_mps + acceleration * acceleration_seconds))
        travel_m = (self.speed_mps + next_speed) * 0.5 * acceleration_seconds
        travel_m += next_speed * (dt - acceleration_seconds)
        self.speed_mps = next_speed
        self.distance_m += travel_m

        steering_seconds = min(dt, travel_m / START_SPEED_MPS)
        next_x = self.x + steering * LATERAL_SPEED_PXPS * steering_seconds
        self.x = min(RIDER_MAX_X, max(RIDER_MIN_X, next_x))
