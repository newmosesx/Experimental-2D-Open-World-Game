import pygame
import sys
import random

from world_structures import world_constants as config # should change this later
import open_world_dir.ui as ui_stable # To initialize UI font

mixer_initialized = False

def init_pygame():
    """Initializes Pygame, Mixer, Font, creates Screen and Clock."""
    global mixer_initialized
    try:
        pygame.init()
        print("Pygame initialized.")
    except Exception as e:
        print(f"FATAL: Pygame initialization failed: {e}")
        sys.exit()

    # Initialize Mixer
    try:
        pygame.mixer.init()
        print("Pygame mixer initialized successfully.")
        mixer_initialized = True
    except pygame.error as e:
        print(f"Error initializing pygame mixer: {e}")
        print("Background music will not be available.")
        mixer_initialized = False

    # Initialize Font (needed for UI and loading screen)
    try:
        pygame.font.init()
        print("Pygame font initialized.")
        ui_stable.init_ui_font() # Initialize the specific UI font
    except Exception as e:
        print(f"Error initializing pygame font system: {e}")
        # Continue without font, UI/Loading text will fail gracefully

    # Create Screen
    try:
        screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Explore the Realm! (Loading...)") # Initial caption
    except pygame.error as e:
        print(f"FATAL: Failed to create screen: {e}")
        pygame.quit()
        sys.exit()

    # Create Clock
    clock = pygame.time.Clock()

    # Seed Random Number Generator
    random.seed(config.RANDOM_SEED)
    print(f"Random seed set to: {config.RANDOM_SEED}")


    return screen, clock, mixer_initialized

def quit_pygame():
    """Cleans up Pygame modules."""
    print("Quitting Pygame...")
    if mixer_initialized:
        pygame.mixer.music.stop() # Stop music before quitting mixer
        pygame.mixer.quit()
        print("Mixer quit.")
    pygame.font.quit()
    print("Font quit.")
    pygame.quit()
    print("Pygame quit.")