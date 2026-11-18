import pygame

from src.config import (
    MAX_FRAME_SECONDS,
    MAX_SPEED_MPS,
    RIDER_HITBOX_HEIGHT,
    RIDER_HITBOX_WIDTH,
    RIDER_SCREEN_Y,
    ROAD_CENTER_X,
    ROAD_LANES,
    ROAD_SCALE_PX_PER_M,
    ROAD_WIDTH,
    TARGET_FPS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.enemies import DoorHazard, DoorPhase
from src.player import Player

BACKGROUND = "#121d1b"
ASPHALT = "#242c2d"
SHOULDER = "#465451"
SIDEWALK = "#2e3b37"
LANE_MARKING = "#687675"
FOREGROUND = "#edf1e6"
MUTED = "#aebdb4"
ACCENT = "#d8f975"
PANEL = "#1b2824"
WARNING = "#ffcf70"
DANGER = "#ff786f"


def draw_road(screen: pygame.Surface, distance_m: float) -> None:
    road_left = ROAD_CENTER_X - ROAD_WIDTH // 2
    road_right = road_left + ROAD_WIDTH
    pygame.draw.rect(screen, SIDEWALK, (road_left - 27, 0, ROAD_WIDTH + 54, WINDOW_HEIGHT))
    pygame.draw.rect(screen, ASPHALT, (road_left, 0, ROAD_WIDTH, WINDOW_HEIGHT))
    pygame.draw.line(screen, SHOULDER, (road_left, 0), (road_left, WINDOW_HEIGHT), 4)
    pygame.draw.line(screen, SHOULDER, (road_right, 0), (road_right, WINDOW_HEIGHT), 4)

    stripe_spacing = 110
    offset = int(distance_m * ROAD_SCALE_PX_PER_M) % stripe_spacing
    for lane in range(1, ROAD_LANES):
        lane_x = road_left + lane * ROAD_WIDTH // ROAD_LANES
        for y in range(offset - stripe_spacing, WINDOW_HEIGHT, stripe_spacing):
            pygame.draw.rect(screen, LANE_MARKING, (lane_x - 2, y, 4, 53))


def draw_rider(screen: pygame.Surface, player: Player, braking: bool) -> None:
    x, y = round(player.x), RIDER_SCREEN_Y
    pygame.draw.ellipse(screen, "#151b1a", (x - 17, y - 25, 38, 54))
    pygame.draw.rect(screen, "#101716", (x - 4, y - 26, 8, 52), border_radius=4)
    pygame.draw.line(screen, "#edf1e6", (x - 12, y - 12), (x + 12, y - 12), 4)
    pygame.draw.rect(screen, ACCENT, (x - 9, y - 8, 18, 25), border_radius=7)
    pygame.draw.circle(screen, FOREGROUND, (x, y - 9), 7)
    if braking and player.speed_mps > 0:
        pygame.draw.circle(screen, DANGER, (x, y + 22), 4)


def draw_door_hazard(
    screen: pygame.Surface,
    hazard: DoorHazard,
    rider_distance_m: float,
    font: pygame.font.Font,
) -> None:
    car = hazard.car_bounds(rider_distance_m)
    car_rect = pygame.Rect(round(car.x), round(car.y), round(car.w), round(car.h))
    if not screen.get_rect().colliderect(car_rect):
        return

    pygame.draw.rect(screen, "#4c6268", car_rect, border_radius=10)
    pygame.draw.rect(screen, BACKGROUND, car_rect.inflate(-14, -35), border_radius=6)
    pygame.draw.line(screen, SHOULDER, car_rect.midtop, car_rect.midbottom, 2)

    phase = hazard.phase
    if phase is DoorPhase.WARNING:
        pygame.draw.rect(screen, WARNING, car_rect, width=3, border_radius=10)
        label = font.render("! Porta", True, WARNING)
        screen.blit(label, (car_rect.right - label.get_width(), car_rect.top - label.get_height() - 6))
    elif phase is DoorPhase.OPEN:
        door = hazard.door_bounds(rider_distance_m)
        door_rect = pygame.Rect(round(door.x), round(door.y), round(door.w), round(door.h))
        pygame.draw.rect(screen, DANGER, door_rect, border_radius=4)
        pygame.draw.line(screen, BACKGROUND, door_rect.midleft, door_rect.midright, 2)


def draw_panel(
    screen: pygame.Surface,
    player: Player,
    title: pygame.font.Font,
    body: pygame.font.Font,
    speed_font: pygame.font.Font,
    door_phase: DoorPhase,
    collided: bool,
) -> None:
    panel = pygame.Rect(748, 115, 448, 540)
    pygame.draw.rect(screen, PANEL, panel, border_radius=22)
    x = panel.x + 34
    screen.blit(title.render("Dead Lane", True, FOREGROUND), (x, 147))

    speed_display = f"{player.speed_mps * 3.6:.0f}"
    label = speed_font.render(speed_display, True, ACCENT)
    screen.blit(label, (x, 226))
    screen.blit(body.render("km/h", True, MUTED), (x + label.get_width() + 12, 271))
    pygame.draw.rect(screen, SHOULDER, (x, 315, 380, 6), border_radius=3)
    progress_width = round(380 * player.speed_mps / MAX_SPEED_MPS)
    if progress_width:
        pygame.draw.rect(screen, ACCENT, (x, 315, progress_width, 6), border_radius=3)

    screen.blit(body.render(f"Distância percorrida   {player.distance_m:.0f} m", True, MUTED), (x, 352))
    pygame.draw.line(screen, SHOULDER, (x, 408), (x + 380, 408))
    for row, (action, keys) in enumerate(
        (
            ("Acelerar", "W / ↑"),
            ("Frear", "S / ↓"),
            ("Mover para os lados", "A D / ← →"),
            ("Reiniciar", "R"),
            ("Sair", "Esc"),
        )
    ):
        y = 430 + row * 36
        screen.blit(body.render(action, True, FOREGROUND), (x, y))
        key_label = body.render(keys, True, MUTED)
        screen.blit(key_label, (x + 380 - key_label.get_width(), y))

    if collided:
        message, color = "Colisão com a porta. R para reiniciar.", DANGER
    elif door_phase is DoorPhase.WARNING:
        message, color = "Aviso de porta. Freie ou mude de faixa.", WARNING
    elif door_phase is DoorPhase.OPEN:
        message, color = "Porta aberta na faixa direita.", DANGER
    else:
        return
    screen.blit(body.render(message, True, color), (x, 617))


def run() -> None:
    pygame.display.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Dead Lane")
        clock = pygame.time.Clock()
        player = Player()
        hazard = DoorHazard()
        collided = False
        rider_bounds = pygame.FRect(0, 0, RIDER_HITBOX_WIDTH, RIDER_HITBOX_HEIGHT)
        rider_bounds.centery = RIDER_SCREEN_Y
        title = pygame.font.SysFont("Segoe UI", 44, bold=True)
        body = pygame.font.SysFont("Segoe UI", 21)
        speed_font = pygame.font.SysFont("Segoe UI", 68, bold=True)

        while True:
            dt = min(clock.tick(TARGET_FPS) / 1000, MAX_FRAME_SECONDS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_r:
                        player = Player()
                        hazard = DoorHazard()
                        collided = False

            brake = False
            if not collided:
                keys = pygame.key.get_pressed()
                left = keys[pygame.K_a] or keys[pygame.K_LEFT]
                right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
                accelerate = keys[pygame.K_w] or keys[pygame.K_UP]
                brake = keys[pygame.K_s] or keys[pygame.K_DOWN]
                player.update(dt, int(right) - int(left), accelerate, brake)
                hazard.update(dt, player.distance_m)
                rider_bounds.centerx = player.x
                if hazard.phase is DoorPhase.OPEN:
                    collided = rider_bounds.colliderect(hazard.door_bounds(player.distance_m))

            screen.fill(BACKGROUND)
            draw_road(screen, player.distance_m)
            draw_door_hazard(screen, hazard, player.distance_m, body)
            draw_rider(screen, player, brake)
            draw_panel(screen, player, title, body, speed_font, hazard.phase, collided)
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
