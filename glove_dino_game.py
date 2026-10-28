"""
Glove-controlled Dino game.

Requires: pip install pygame pyserial

Controls (from the glove, over serial):
    Index finger bend  -> Jump
    Middle+ring+pinky   -> Duck (hold)
    Thumb bend          -> Restart on the game-over screen

Keyboard fallback (works even with no Arduino connected):
    Space -> Jump
    Down arrow -> Duck (hold)
    R -> Restart on the game-over screen
"""

import random
import threading
import time

import pygame

try:
    import serial
except ImportError:
    serial = None

# ---------------- Serial setup ----------------
SERIAL_PORT = "COM3"   # Windows example. On Linux/Mac try "/dev/ttyUSB0" or "/dev/ttyACM0"
BAUD_RATE = 9600

ser = None
if serial is not None:
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)  # allow the Arduino to reset after the port opens
        print(f"Connected to glove on {SERIAL_PORT}")
    except Exception as e:
        print(f"Could not open serial port {SERIAL_PORT}: {e}")
        print("Running in keyboard-only fallback mode.")
else:
    print("pyserial not installed - running in keyboard-only fallback mode.")

control_state = {"jump": False, "duck": False, "restart": False}
lock = threading.Lock()


def serial_reader():
    global ser
    while True:
        try:
            if ser and ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                with lock:
                    if line == "J":
                        control_state["jump"] = True
                    elif line == "D":
                        control_state["duck"] = True
                    elif line == "d":
                        control_state["duck"] = False
                    elif line == "T":
                        control_state["restart"] = True
        except Exception as e:
            # Uno R4 (and other native-USB boards) can briefly drop the
            # connection on reset - reconnect instead of killing the thread.
            print(f"Serial hiccup ({e}) - reconnecting...")
            try:
                if ser:
                    ser.close()
            except Exception:
                pass
            time.sleep(1)
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                time.sleep(2)
                print("Reconnected to glove.")
            except Exception as e2:
                print(f"Reconnect failed ({e2}), will retry...")
                ser = None
                time.sleep(1)
        time.sleep(0.01)


if ser:
    threading.Thread(target=serial_reader, daemon=True).start()


def send_feedback(cmd):
    if ser:
        try:
            ser.write(cmd.encode())
        except Exception as e:
            print(f"Serial write failed: {e}")


# ---------------- Game setup ----------------
pygame.init()
WIDTH, HEIGHT = 800, 300
GROUND_Y = 230
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Glove Dino")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 24)

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
GRAY = (120, 120, 120)
SKY_BLUE = (90, 90, 220)
GREEN = (40, 180, 90)
RED = (200, 40, 40)

led_state = "G"          # mirrors what we last told the Arduino: G/A/L
last_action_time = 0.0
ACTION_FLASH_SECONDS = 0.2

INITIAL_SPEED = 6
MAX_SPEED = 16
SPEED_RAMP_PER_FRAME = 0.002  # smooth, gradual acceleration instead of sudden jumps


def trigger_action():
    """Call this exactly when a jump or duck actually happens."""
    global last_action_time, led_state
    last_action_time = time.time()
    led_state = "A"
    send_feedback("A")


def current_indicator_color(is_game_over):
    if is_game_over:
        return RED
    if time.time() - last_action_time < ACTION_FLASH_SECONDS:
        return SKY_BLUE
    return GREEN


class Dino:
    def __init__(self):
        self.x = 60
        self.width, self.height = 40, 50
        self.duck_height = 25
        self.y = GROUND_Y - self.height
        self.vel_y = 0
        self.on_ground = True
        self.ducking = False

    def jump(self):
        if self.on_ground:
            self.vel_y = -13
            self.on_ground = False
            return True
        return False

    def set_duck(self, ducking):
        self.ducking = ducking and self.on_ground

    def update(self):
        h = self.duck_height if self.ducking else self.height
        self.y += self.vel_y
        self.vel_y += 0.6  # gravity
        if self.y >= GROUND_Y - h:
            self.y = GROUND_Y - h
            self.vel_y = 0
            self.on_ground = True

    def rect(self):
        h = self.duck_height if self.ducking else self.height
        return pygame.Rect(self.x, self.y, self.width, h)

    def draw(self, surf):
        pygame.draw.rect(surf, BLACK, self.rect())


class Obstacle:
    def __init__(self, x, kind=None):
        self.kind = kind or random.choice(["ground", "ground", "flying"])  # ground obstacles a bit more common
        self.x = x
        if self.kind == "ground":
            self.width = random.choice([20, 25, 30])
            self.height = random.choice([30, 40, 50])
            self.y = GROUND_Y - self.height
        else:  # "flying" - sits at standing-dino head height; only a duck clears it
            self.width = random.choice([28, 34])
            self.height = 20
            self.y = GROUND_Y - 50

    def update(self, speed):
        self.x -= speed

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surf):
        color = GRAY if self.kind == "ground" else SKY_BLUE
        pygame.draw.rect(surf, color, self.rect())


def reset_game():
    return Dino(), [], 0, INITIAL_SPEED, False  # dino, obstacles, score, speed, game_over


dino, obstacles, score, speed, game_over = reset_game()
spawn_timer = 0
game_over_notified = False
was_ducking = False
send_feedback("G")  # tell the glove we're in the running state

running = True
while running:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                control_state["jump"] = True
            if event.key == pygame.K_r and game_over:
                control_state["restart"] = True
            if event.key == pygame.K_DOWN:
                control_state["duck"] = True
        if event.type == pygame.KEYUP and event.key == pygame.K_DOWN:
            control_state["duck"] = False

    with lock:
        do_jump = control_state["jump"]
        do_duck = control_state["duck"]
        do_restart = control_state["restart"]
        control_state["jump"] = False
        control_state["restart"] = False

    if not game_over:
        if do_jump:
            if dino.jump():
                trigger_action()  # blue flash + buzzer + vibration
        dino.set_duck(do_duck)
        if dino.ducking and not was_ducking:
            trigger_action()  # duck just engaged
        was_ducking = dino.ducking
        dino.update()

        spawn_timer += 1
        if spawn_timer > max(40, 90 - speed * 3):
            obstacles.append(Obstacle(WIDTH + 20))
            spawn_timer = 0

        for obs in obstacles:
            obs.update(speed)
        obstacles = [o for o in obstacles if o.x + o.width > 0]

        score += 1
        if speed < MAX_SPEED:
            speed += SPEED_RAMP_PER_FRAME

        for obs in obstacles:
            if dino.rect().colliderect(obs.rect()):
                game_over = True
                game_over_notified = False
    else:
        if not game_over_notified:
            send_feedback("L")  # lose feedback -> red LED + buzzer + vibration
            led_state = "L"
            game_over_notified = True
        if do_restart:
            dino, obstacles, score, speed, game_over = reset_game()
            spawn_timer = 0
            was_ducking = False
            send_feedback("G")  # back to running state

    # ---------------- Draw ----------------
    screen.fill(WHITE)
    pygame.draw.line(screen, BLACK, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
    dino.draw(screen)
    for obs in obstacles:
        obs.draw(screen)

    # Small on-screen dot mirrors the glove's LED: green=running, blue=action, red=dead
    pygame.draw.circle(screen, current_indicator_color(game_over), (30, 30), 12)

    score_surf = font.render(f"Score: {score}", True, BLACK)
    screen.blit(score_surf, (WIDTH - 160, 20))

    if game_over:
        over_surf = font.render("GAME OVER - bend thumb (or press R) to restart", True, (200, 0, 0))
        screen.blit(over_surf, (WIDTH // 2 - 260, HEIGHT // 2 - 20))

    pygame.display.flip()

pygame.quit()
if ser:
    ser.close()