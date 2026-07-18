import pygame
import random
import sys
import math

# Initialize Pygame
pygame.init()
pygame.font.init()

# --- Configuration Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
FPS = 60

# Colors (Hex / RGB)
BG_COLOR = (40, 40, 40)
ROAD_COLOR = (80, 80, 80)
LINE_COLOR = (240, 240, 240)
TEXT_COLOR = (255, 255, 255)

RED = (255, 50, 50)
YELLOW = (255, 200, 50)
GREEN = (50, 255, 50)
GRAY = (100, 100, 100)

# Road Geography
ROAD_WIDTH = 120
HALF_RW = ROAD_WIDTH // 2
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

# Traffic Timing (in frames, 60 frames = 1 second)
GREEN_TIME = 300   # 5 seconds
YELLOW_TIME = 120  # 2 seconds

# --- Vehicle Class ---
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, direction):
        super().__init__()
        self.direction = direction # 'N', 'S', 'E', 'W' (Origin direction)
        self.speed = random.uniform(2.5, 4.0)
        self.max_speed = self.speed
        self.width = 25
        self.height = 15
        
        # Orient vehicle dimensions based on movement path
        if self.direction in ['N', 'S']:
            self.image = pygame.Surface((self.height, self.width))
            self.image.fill((random.randint(50, 200), random.randint(50, 200), random.randint(150, 255)))
        else:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((random.randint(150, 255), random.randint(50, 200), random.randint(50, 200)))
            
        self.rect = self.image.get_rect()
        self.has_stopped = False
        self.wait_time = 0

        # Set spawn coordinates and movement tracking bounds
        if self.direction == 'W': # Spawns West, moves East
            self.rect.x = -self.width
            self.rect.y = CENTER_Y + 15
            self.stop_line = CENTER_X - HALF_RW - 15
        elif self.direction == 'E': # Spawns East, moves West
            self.rect.x = SCREEN_WIDTH + self.width
            self.rect.y = CENTER_Y - 30
            self.stop_line = CENTER_X + HALF_RW + 15
        elif self.direction == 'N': # Spawns North, moves South
            self.rect.x = CENTER_X - 30
            self.rect.y = -self.width
            self.stop_line = CENTER_Y - HALF_RW - 15
        elif self.direction == 'S': # Spawns South, moves North
            self.rect.x = CENTER_X + 15
            self.rect.y = SCREEN_HEIGHT + self.width
            self.stop_line = CENTER_Y + HALF_RW + 15

    def update(self, lights, lead_vehicle):
        # Determine active state of the traffic light facing this vehicle
        is_red = (self.direction in ['E', 'W'] and lights['current_phase'] == 'NS') or \
                 (self.direction in ['N', 'S'] and lights['current_phase'] == 'EW')
        is_yellow = lights['is_yellow']

        # Determine target velocity based on traffic signal state
        target_speed = self.max_speed
        
        # 1. Check Light Conditions at Intersection Stop Line
        if (is_red or is_yellow):
            if self.direction == 'W' and self.rect.right < self.stop_line and self.rect.right >= self.stop_line - 100:
                target_speed = 0
            elif self.direction == 'E' and self.rect.left > self.stop_line and self.rect.left <= self.stop_line + 100:
                target_speed = 0
            elif self.direction == 'N' and self.rect.bottom < self.stop_line and self.rect.bottom >= self.stop_line - 100:
                target_speed = 0
            elif self.direction == 'S' and self.rect.top > self.stop_line and self.rect.top <= self.stop_line + 100:
                target_speed = 0

        # 2. Prevent Collisions (Adaptive Safety Buffers)
        if lead_vehicle:
            buffer = 20
            if self.direction == 'W' and lead_vehicle.rect.left - self.rect.right < self.width + buffer:
                target_speed = min(target_speed, lead_vehicle.speed)
            elif self.direction == 'E' and self.rect.left - lead_vehicle.rect.right < self.width + buffer:
                target_speed = min(target_speed, lead_vehicle.speed)
            elif self.direction == 'N' and lead_vehicle.rect.top - self.rect.bottom < self.width + buffer:
                target_speed = min(target_speed, lead_vehicle.speed)
            elif self.direction == 'S' and self.rect.top - lead_vehicle.rect.bottom < self.width + buffer:
                target_speed = min(target_speed, lead_vehicle.speed)

        # Apply smooth linear deceleration/acceleration curves
        if self.speed > target_speed:
            self.speed = max(target_speed, self.speed - 0.2)
        elif self.speed < target_speed:
            self.speed = min(target_speed, self.speed + 0.1)

        # Execute coordinate translation adjustments
        if self.direction == 'W': self.rect.x += math.floor(self.speed)
        elif self.direction == 'E': self.rect.x -= math.floor(self.speed)
        elif self.direction == 'N': self.rect.y += math.floor(self.speed)
        elif self.direction == 'S': self.rect.y -= math.floor(self.speed)

        # Metric Collection
        if self.speed < 0.5:
            self.wait_time += 1

        # Garbage Collector: Purge off-screen sprite instances
        if (self.rect.x > SCREEN_WIDTH + 50 or self.rect.x < -100 or 
            self.rect.y > SCREEN_HEIGHT + 50 or self.rect.y < -100):
            self.kill()

# --- Core Simulation Engine Class ---
class TrafficSimulation:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("4-Way Intersection System Model")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 16)
        
        # Sprite Containers
        self.vehicles = pygame.sprite.Group()
        
        # Traffic Light Machine State Array
        self.lights = {
            'current_phase': 'NS',  # 'NS' stands for North-South Green, 'EW' for East-West Green
            'is_yellow': False,
            'timer': GREEN_TIME
        }
        
        # System Telemetry Counters
        self.total_delay_frames = 0
        self.spawn_probability = 0.03 # Adjust this variable to modulate density constraints

    def update_lights(self):
        self.lights['timer'] -= 1
        if self.lights['timer'] <= 0:
            if not self.lights['is_yellow']:
                self.lights['is_yellow'] = True
                self.lights['timer'] = YELLOW_TIME
            else:
                self.lights['is_yellow'] = False
                self.lights['timer'] = GREEN_TIME
                # Toggle phase execution flags
                self.lights['current_phase'] = 'EW' if self.lights['current_phase'] == 'NS' else 'NS'

    def spawn_vehicles(self):
        if random.random() < self.spawn_probability:
            direction = random.choice(['N', 'S', 'E', 'W'])
            
            # Check for adjacent safe spacing margins before allowing a structural instantiation
            safe_spawn = True
            for v in self.vehicles:
                if v.direction == direction:
                    if direction == 'W' and v.rect.x < 60: safe_spawn = False
                    elif direction == 'E' and v.rect.x > SCREEN_WIDTH - 60: safe_spawn = False
                    elif direction == 'N' and v.rect.y < 60: safe_spawn = False
                    elif direction == 'S' and v.rect.y > SCREEN_HEIGHT - 60: safe_spawn = False
            
            if safe_spawn:
                new_car = Vehicle(direction)
                self.vehicles.add(new_car)

    def draw_environment(self):
        self.screen.fill(BG_COLOR)
        
        # Draw Intersecting Road Boundaries
        pygame.draw.rect(self.screen, ROAD_COLOR, (CENTER_X - HALF_RW, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.rect(self.screen, ROAD_COLOR, (0, CENTER_Y - HALF_RW, SCREEN_WIDTH, ROAD_WIDTH))
        
        # Draw Separator Lines (Dashed Centers)
        for i in range(0, SCREEN_HEIGHT, 30):
            if i < CENTER_Y - HALF_RW or i > CENTER_Y + HALF_RW:
                pygame.draw.line(self.screen, LINE_COLOR, (CENTER_X, i), (CENTER_X, i + 15), 2)
        for i in range(0, SCREEN_WIDTH, 30):
            if i < CENTER_X - HALF_RW or i > CENTER_X + HALF_RW:
                pygame.draw.line(self.screen, LINE_COLOR, (i, CENTER_Y), (i + 15, CENTER_Y), 2)

        # Draw Stop Lines at the margins
        pygame.draw.line(self.screen, LINE_COLOR, (CENTER_X - HALF_RW, CENTER_Y + HALF_RW), (CENTER_X, CENTER_Y + HALF_RW), 3) # South Bound Stop
        pygame.draw.line(self.screen, LINE_COLOR, (CENTER_X, CENTER_Y - HALF_RW), (CENTER_X + HALF_RW, CENTER_Y - HALF_RW), 3) # North Bound Stop
        pygame.draw.line(self.screen, LINE_COLOR, (CENTER_X - HALF_RW, CENTER_Y - HALF_RW), (CENTER_X - HALF_RW, CENTER_Y), 3) # West Bound Stop
        pygame.draw.line(self.screen, LINE_COLOR, (CENTER_X + HALF_RW, CENTER_Y), (CENTER_X + HALF_RW, CENTER_Y + HALF_RW), 3) # East Bound Stop

    def draw_traffic_lights(self):
        ns_color = RED if self.lights['current_phase'] == 'EW' else (YELLOW if self.lights['is_yellow'] else GREEN)
        ew_color = RED if self.lights['current_phase'] == 'NS' else (YELLOW if self.lights['is_yellow'] else GREEN)
        
        # Visual Coordinates for the Signal Modules
        light_positions = {
            'N': (CENTER_X - HALF_RW - 20, CENTER_Y - HALF_RW - 20),
            'S': (CENTER_X + HALF_RW + 20, CENTER_Y + HALF_RW + 20),
            'E': (CENTER_X + HALF_RW + 20, CENTER_Y - HALF_RW - 20),
            'W': (CENTER_X - HALF_RW - 20, CENTER_Y + HALF_RW + 20)
        }
        
        for key, pos in light_positions.items():
            color = ns_color if key in ['N', 'S'] else ew_color
            pygame.draw.circle(self.screen, (0, 0, 0), pos, 14)
            pygame.draw.circle(self.screen, color, pos, 10)

    def render_telemetry(self, current_queues):
        metrics = [
            f"Active Signal Corridor: {'North-South' if self.lights['current_phase'] == 'NS' else 'East-West'}",
            f"Phase Countdown Time  : {max(0, self.lights['timer'] // 60)}s",
            f"Active Queue Load     : {sum(current_queues.values())} vehicles",
            f"Accumulated Latency   : {self.total_delay_frames // 60}s vehicle-wait-time",
            "---------------------------------------",
            f"Queue Distribution -> N:{current_queues['N']} S:{current_queues['S']} E:{current_queues['E']} W:{current_queues['W']}"
        ]
        
        # Background Overlay Panel
        pygame.draw.rect(self.screen, (15, 15, 15), (10, 10, 480, 140))
        for index, text in enumerate(metrics):
            surface = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(surface, (20, 15 + (index * 18)))

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            
            # Catch Interrupt Handlers
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # Operational Updates
            self.update_lights()
            self.spawn_vehicles()

            # Dynamic Queue Optimization Calculations
            queues = {'N': 0, 'S': 0, 'E': 0, 'W': 0}
            sorted_vehicles = {'N': [], 'S': [], 'E': [], 'W': []}
            
            # Map vehicles by direction and sort based on closeness to intersection
            for v in self.vehicles:
                sorted_vehicles[v.direction].append(v)
                if v.speed < 0.5:
                    queues[v.direction] += 1
                    self.total_delay_frames += 1

            # Sort vehicle arrays so index 0 is always closest to the intersection line
            for d in ['W', 'E', 'N', 'S']:
                if d == 'W': sorted_vehicles[d].sort(key=lambda x: x.rect.x, reverse=True)
                elif d == 'E': sorted_vehicles[d].sort(key=lambda x: x.rect.x)
                elif d == 'N': sorted_vehicles[d].sort(key=lambda x: x.rect.y, reverse=True)
                elif d == 'S': sorted_vehicles[d].sort(key=lambda x: x.rect.y)

            # Update vehicle physics relative to the preceding car in their corridor
            for direction, car_list in sorted_vehicles.items():
                for idx, car in enumerate(car_list):
                    lead = None if idx == 0 else car_list[idx - 1]
                    car.update(self.lights, lead)

            # Rendering Passes
            self.draw_environment()
            self.vehicles.draw(self.screen)
            self.draw_traffic_lights()
            self.render_telemetry(queues)
            
            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    simulation = TrafficSimulation()
    simulation.run()