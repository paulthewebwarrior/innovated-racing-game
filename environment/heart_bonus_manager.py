import os
import random

import pygame

from models.road import Road


class HeartBonus(pygame.sprite.Sprite):
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        image: pygame.Surface | None = None,
    ):
        super().__init__()
        self.width = width
        self.height = height
        if image:
            self.image = image
            self.rect = self.image.get_rect()
        else:
            self.image = pygame.Surface((width, height), pygame.SRCALPHA)
            self.rect = pygame.Rect(x, y, width, height)
        self.rect.x = x
        self.rect.y = y

    def update(self, speed: int, road_height: int) -> None:
        self.rect.y += speed
        if self.rect.top > road_height:
            self.kill()


class HeartBonusManager:
    def __init__(
        self,
        road: Road,
        spawn_frequency: int = 600,
        max_hearts: int = 1,
    ):
        self.road = road
        self.spawn_frequency = max(60, spawn_frequency)
        self.max_hearts = max_hearts
        self.hearts = pygame.sprite.Group()
        self.timer = 0
        self._heart_image = self._load_heart_image()
        self.heart_width = 40
        self.heart_height = 40
        if self._heart_image:
            self.heart_width = self._heart_image.get_width()
            self.heart_height = self._heart_image.get_height()

    def _load_heart_image(self) -> pygame.Surface | None:
        filepath = os.path.join("resources", "models", "full hp.png")
        if os.path.exists(filepath):
            try:
                img = pygame.image.load(filepath).convert_alpha()
                return img
            except pygame.error:
                pass
        return None

    def _spawn_heart(self) -> None:
        lane = self.road.get_lane(random.randint(0, self.road.lane_count - 1))
        lane_center = lane.left + lane.width // 2
        spawn_x = lane_center - self.heart_width // 2
        spawn_x = self.road.clamp_spawn_x_to_borders(spawn_x, self.heart_width)
        spawn_y = -self.heart_height - random.randint(50, 150)

        heart = HeartBonus(
            spawn_x,
            spawn_y,
            self.heart_width,
            self.heart_height,
            image=self._heart_image,
        )
        self.hearts.add(heart)

    def update(self, speed: int) -> None:
        self.timer += 1
        if self.timer >= self.spawn_frequency:
            self.timer = 0
            if len(self.hearts) < self.max_hearts:
                self._spawn_heart()

        self.hearts.update(speed, self.road.height)

    def draw(self, surface: pygame.Surface) -> None:
        self.hearts.draw(surface)

    def get_hearts(self) -> pygame.sprite.Group:
        return self.hearts

    def clear(self) -> None:
        self.hearts.empty()
