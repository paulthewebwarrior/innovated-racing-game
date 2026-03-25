from __future__ import annotations

from typing import Optional
import math

import pygame

import config
from models.player_car import PlayerCar
from controller import Controller


class PlayerHUD:
    def __init__(
        self,
        player_car: PlayerCar,
        controller: Controller,
        font: pygame.font.Font,
        position: tuple[int, int] = (10, 10),
        size: tuple[int, int] = (320, 260),
        camera_preview_size: tuple[int, int] = (180, 135),
        show_camera_preview: bool = True,
    ) -> None:
        self.speed = player_car.current_speed
        self.max_speed = player_car.max_speed
        self.is_braking = controller.breaking
        self.steer = controller.steer
        self.gear: str = "1"
        self.left_shift_active = controller.left_shift_active
        self.right_shift_active = controller.right_shift_active
        self.acceleration = 0.0
        self._last_speed = float(self.speed)
        self.score: Optional[int] = None
        self.lives: Optional[float] = None
        self.fps: Optional[int] = None
        self.max_fps: Optional[int] = None
        self._camera_frame = None
        self.combo: float = 1.0
        self.difficulty: float = 1.0
        self.distance: float = 0.0
        self._bonus_pulse = 0.0
        self._pulse_direction = 1

        self.font = font
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 20)
        self.position = position
        self.size = size
        self.camera_preview_size = camera_preview_size
        self.show_camera_preview = show_camera_preview

        self._bg_color = (10, 10, 20, 200)
        self._panel_bg = (15, 15, 30, 220)
        self._text_color = (230, 230, 240)
        self._accent_color = (0, 210, 255)
        self._accent_glow = (0, 150, 200)
        self._warn_color = (255, 70, 70)
        self._success_color = (70, 255, 140)
        self._gold_color = (255, 200, 50)
        self._muted_color = (100, 100, 120)

        self._score_panel_surf: Optional[pygame.Surface] = None
        self._score_panel_size = (280, 120)
        self._stats_panel_surf: Optional[pygame.Surface] = None
        self._stats_panel_size = (200, 100)
        self._speedometer_surf: Optional[pygame.Surface] = None
        self._speedometer_size = (160, 160)
        self._lives_surf: Optional[pygame.Surface] = None
        self._last_lives: Optional[float] = None
        self._needs_panel_update = True

    def update_from_game(
        self,
        player_car: PlayerCar,
        controller: Controller,
        gear: Optional[str] = None,
        score: Optional[int] = None,
        lives: Optional[float] = None,
        fps: Optional[int] = None,
        max_fps: Optional[int] = None,
    ) -> None:
        self.speed = player_car.current_speed
        delta_speed = float(self.speed) - self._last_speed
        self.max_speed = player_car.max_speed
        self.is_braking = controller.breaking
        self.steer = controller.steer
        self.left_shift_active = controller.left_shift_active
        self.right_shift_active = controller.right_shift_active
        if gear is not None:
            self.gear = gear
        else:
            self.gear = self._compute_gear(self.speed, self.max_speed)
        self.score = score
        self.lives = lives
        self.fps = fps
        self.max_fps = max_fps
        if self.fps is not None and self.fps > 0:
            self.acceleration = delta_speed * float(self.fps)
        else:
            self.acceleration = delta_speed
        self._last_speed = float(self.speed)
        self._camera_frame = (
            controller.get_frame() if self.show_camera_preview else None
        )

    def set_speed(self, current_speed: float, max_speed: float) -> None:
        self.speed = current_speed
        self.max_speed = max_speed

    def set_scoring_info(
        self, combo: float, difficulty: float, distance: float
    ) -> None:
        self.combo = combo
        self.difficulty = difficulty
        self.distance = distance

    def _update_pulse(self, dt: float) -> None:
        self._bonus_pulse += dt * 3.0 * self._pulse_direction
        if self._bonus_pulse >= 1.0:
            self._bonus_pulse = 1.0
            self._pulse_direction = -1
        elif self._bonus_pulse <= 0.0:
            self._bonus_pulse = 0.0
            self._pulse_direction = 1

    def draw(self, screen: pygame.Surface) -> None:
        self._update_pulse(0.016)
        screen_w, screen_h = screen.get_size()
        self._draw_score_panel_top_right(screen)
        self._draw_speedometer_center_top(screen)
        self._draw_stats_panel_bottom_left(screen)
        self._draw_gesture_indicator_bottom_right(screen)
        if self.show_camera_preview:
            self._draw_camera_preview_bottom_right(screen, self.camera_preview_size)
        self._draw_lives_top_left(screen)

    def _draw_simple_panel(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        bg_alpha: int = 180,
    ) -> None:
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        bg = (15, 15, 30, bg_alpha)
        panel.fill(bg)
        pygame.draw.rect(panel, (40, 40, 60), panel.get_rect(), 1, border_radius=10)
        surface.blit(panel, (x, y))

    def _draw_score_panel_top_right(self, screen: pygame.Surface) -> None:
        panel_w, panel_h = self._score_panel_size
        margin = 20
        x = screen.get_width() - panel_w - margin
        y = margin

        if self._score_panel_surf is None:
            self._score_panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            self._needs_panel_update = True

        if self._needs_panel_update or True:
            self._score_panel_surf.fill((0, 0, 0, 0))

            bg = (15, 15, 30, 220)
            pygame.draw.rect(
                self._score_panel_surf, bg, (0, 0, panel_w, panel_h), border_radius=12
            )
            pygame.draw.rect(
                self._score_panel_surf,
                (40, 40, 60),
                (0, 0, panel_w, panel_h),
                1,
                border_radius=12,
            )
            pygame.draw.rect(
                self._score_panel_surf,
                self._accent_color,
                (0, 0, panel_w, 3),
                border_radius=12,
            )

            score_text = f"{self.score or 0:,}"
            score_surf = self.font_large.render(score_text, True, self._text_color)
            label_surf = self.font_small.render("SCORE", True, self._muted_color)

            self._score_panel_surf.blit(label_surf, (20, 12))
            self._score_panel_surf.blit(score_surf, (20, 30))

            combo_active = self.combo > 1.0
            if combo_active:
                pulse_alpha = int(150 + 105 * self._bonus_pulse)
                combo_color = (
                    self._accent_color
                    if self.combo < 3.0
                    else self._gold_color
                    if self.combo < 4.0
                    else self._warn_color
                )
                combo_text = f"x{self.combo:.1f}"
                combo_surf = self.font_medium.render(combo_text, True, combo_color)
                self._score_panel_surf.blit(combo_surf, (20, 85))

            if self.difficulty > 1.0:
                diff_text = f"DIFF x{self.difficulty:.2f}"
                diff_surf = self.font_small.render(diff_text, True, self._muted_color)
                dx = 100 if combo_active else 20
                self._score_panel_surf.blit(diff_surf, (dx, 90))

        screen.blit(self._score_panel_surf, (x, y))

    def _draw_speedometer_center_top(self, screen: pygame.Surface) -> None:
        screen_w = screen.get_width()
        radius = 65
        center_x = screen_w // 2
        center_y = radius + 15

        if self._speedometer_surf is None:
            self._speedometer_surf = pygame.Surface(
                (radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA
            )

        self._speedometer_surf.fill((0, 0, 0, 0))
        surf = self._speedometer_surf
        offset = 10
        cx = radius + offset
        cy = radius + offset

        pygame.draw.circle(surf, (20, 20, 30), (cx, cy), radius + 8)
        pygame.draw.circle(surf, (30, 30, 50), (cx, cy), radius)

        start_angle = math.radians(135)
        end_angle = math.radians(405)
        rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        pygame.draw.arc(surf, (50, 50, 70), rect, start_angle, end_angle, 6)

        tick_count = 10
        for i in range(tick_count + 1):
            tick_ratio = i / tick_count
            tick_angle = start_angle + (end_angle - start_angle) * tick_ratio
            inner_r = radius - 15
            outer_r = radius - 5
            x1 = cx + int(inner_r * math.cos(tick_angle))
            y1 = cy - int(inner_r * math.sin(tick_angle))
            x2 = cx + int(outer_r * math.cos(tick_angle))
            y2 = cy - int(outer_r * math.sin(tick_angle))
            pygame.draw.line(surf, (80, 80, 100), (x1, y1), (x2, y2), 2)

        ratio = max(0.0, min(self.speed / max(1, self.max_speed), 1.0))
        needle_end_angle = start_angle + (end_angle - start_angle) * ratio
        needle_len = radius - 18
        nx = cx + int(needle_len * math.cos(needle_end_angle))
        ny = cy - int(needle_len * math.sin(needle_end_angle))

        needle_color = self._warn_color if self.is_braking else self._accent_color
        pygame.draw.line(surf, needle_color, (cx, cy), (nx, ny), 4)
        pygame.draw.circle(surf, needle_color, (cx, cy), 8)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 4)

        speed_str = f"{self.speed:.0f}"
        speed_surf = self.font_large.render(speed_str, True, self._text_color)
        speed_rect = speed_surf.get_rect(center=(cx, cy + 15))
        surf.blit(speed_surf, speed_rect)

        unit_surf = self.font_small.render("km/h", True, self._muted_color)
        unit_rect = unit_surf.get_rect(center=(cx, cy + 35))
        surf.blit(unit_surf, unit_rect)

        screen.blit(
            self._speedometer_surf,
            (center_x - radius - offset, center_y - radius - offset),
        )

    def _draw_stats_panel_bottom_left(self, screen: pygame.Surface) -> None:
        panel_w, panel_h = self._stats_panel_size
        margin = 20
        x = margin
        y = screen.get_height() - panel_h - margin

        if self._stats_panel_surf is None:
            self._stats_panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

        self._stats_panel_surf.fill((0, 0, 0, 0))
        bg = (15, 15, 30, 200)
        pygame.draw.rect(
            self._stats_panel_surf, bg, (0, 0, panel_w, panel_h), border_radius=10
        )
        pygame.draw.rect(
            self._stats_panel_surf,
            (50, 50, 70),
            (0, 0, panel_w, panel_h),
            1,
            border_radius=10,
        )

        line_h = 22
        col1_x = 15
        col2_x = panel_w // 2 + 5
        start_y = 15

        labels = ["SPD", "GEAR", "DIST"]
        values = [f"{self.speed:.0f}", self.gear, f"{int(self.distance)}m"]

        for i, (label, value) in enumerate(zip(labels, values)):
            lx = col1_x if i % 2 == 0 else col2_x
            ly = start_y + (i // 2) * (line_h + 12)
            self._stats_panel_surf.blit(
                self.font_small.render(label, True, self._muted_color), (lx, ly)
            )
            self._stats_panel_surf.blit(
                self.font_medium.render(value, True, self._text_color), (lx, ly + 15)
            )

        screen.blit(self._stats_panel_surf, (x, y))

    def _draw_gesture_indicator_bottom_right(self, screen: pygame.Surface) -> None:
        margin = 20
        icon_size = 42
        spacing = 8
        icon_count = 2
        total_w = icon_size * icon_count + spacing * (icon_count - 1)

        cam_offset = (
            self.camera_preview_size[0] + margin if self.show_camera_preview else 0
        )
        start_x = screen.get_width() - total_w - margin - cam_offset
        start_y = screen.get_height() - icon_size - margin

        if self.is_braking:
            self._draw_gesture_icon_simple(
                screen, (start_x, start_y), icon_size, "brake", self._warn_color
            )
        else:
            self._draw_gesture_icon_simple(
                screen, (start_x, start_y), icon_size, "throttle", self._accent_color
            )

        steer_dir = (
            "left" if self.steer < -0.4 else "right" if self.steer > 0.4 else "center"
        )
        self._draw_gesture_icon_simple(
            screen,
            (start_x + icon_size + spacing, start_y),
            icon_size,
            "steer",
            steer_dir,
        )

    def _draw_gesture_icon_simple(
        self, screen: pygame.Surface, pos: tuple, size: int, icon_type: str, state
    ) -> None:
        x, y = pos
        rect = pygame.Rect(x, y, size, size)

        bg_color = (25, 25, 40) if icon_type != "brake" else (50, 20, 20)
        border_color = (
            state
            if isinstance(state, tuple)
            else (self._accent_color if state != "center" else self._muted_color)
        )

        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        cx, cy = x + size // 2, y + size // 2

        if icon_type == "brake":
            pygame.draw.circle(screen, self._warn_color, (cx, cy), size // 4)
        elif icon_type == "throttle":
            inner = size // 4
            bar_h = size // 2
            bar_rect = pygame.Rect(cx - inner, cy + inner // 2, inner * 2, bar_h)
            pygame.draw.rect(screen, border_color, bar_rect, border_radius=3)
        elif icon_type == "steer":
            if state == "left":
                pts = [(cx - 8, cy), (cx + 6, cy - 8), (cx + 6, cy + 8)]
            elif state == "right":
                pts = [(cx + 8, cy), (cx - 6, cy - 8), (cx - 6, cy + 8)]
            else:
                pygame.draw.circle(screen, self._muted_color, (cx, cy), 5)
                return
            pygame.draw.polygon(screen, border_color, pts)

    def _draw_lives_top_left(self, screen: pygame.Surface) -> None:
        if self.lives is None:
            return

        if self._lives_surf is None or self._last_lives != self.lives:
            self._last_lives = self.lives
            max_hearts = max(1, int(config.MAX_HEARTS), int(config.STARTING_LIVES))
            clamped_lives = max(0.0, min(float(max_hearts), float(self.lives)))
            full_hearts = int(clamped_lives)
            has_half = (clamped_lives - full_hearts) >= 0.5
            empty_hearts = max_hearts - full_hearts - (1 if has_half else 0)

            heart_size = 24
            spacing = 4
            surf_w = max_hearts * heart_size + (max_hearts - 1) * spacing
            surf_h = self.font_small.get_height() + 5 + heart_size + 10

            self._lives_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            self._lives_surf.fill((0, 0, 0, 0))

            label = self.font_small.render("LIVES", True, self._muted_color)
            self._lives_surf.blit(label, (0, 0))

            for i in range(full_hearts):
                char_surf = self.font_medium.render("●", True, self._warn_color)
                self._lives_surf.blit(char_surf, (i * (heart_size + spacing), 18))
            if has_half:
                char_surf = self.font_medium.render("◐", True, self._warn_color)
                self._lives_surf.blit(
                    char_surf, (full_hearts * (heart_size + spacing), 18)
                )
            for i in range(empty_hearts):
                char_surf = self.font_medium.render("○", True, (60, 60, 70))
                offset = (full_hearts + (1 if has_half else 0)) * (heart_size + spacing)
                self._lives_surf.blit(
                    char_surf, (offset + i * (heart_size + spacing), 18)
                )

        screen.blit(self._lives_surf, (15, 15))

    def _compute_gear(self, speed: float, max_speed: float) -> str:
        if speed <= 0.1:
            return "N"
        if max_speed <= 0:
            return "1"
        ratio = max(0.0, min(speed / max_speed, 1.0))
        gear = 1 + int(ratio * 4.999)
        return str(min(5, max(1, gear)))

    def _draw_camera_preview(
        self,
        screen: pygame.Surface,
        top_left: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        x, y = top_left
        w, h = size
        border = pygame.Rect(x - 2, y - 2, w + 4, h + 4)
        pygame.draw.rect(screen, (20, 20, 20), border)
        pygame.draw.rect(screen, self._accent_color, border, 2)

        if self._camera_frame is None:
            label = self.font.render("Camera", True, self._muted_color)
            screen.blit(label, (x + 8, y + 8))
            return

        try:
            import cv2
        except ImportError:
            return

        try:
            frame_rgb = cv2.cvtColor(self._camera_frame, cv2.COLOR_BGR2RGB)
        except cv2.error:
            return

        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        surf = pygame.transform.smoothscale(surf, (w, h))
        screen.blit(surf, (x, y))

    def _draw_camera_preview_bottom_right(
        self,
        screen: pygame.Surface,
        size: tuple[int, int],
    ) -> None:
        margin = 16
        w, h = size
        top_left = (screen.get_width() - w - margin, screen.get_height() - h - margin)
        self._draw_camera_preview(screen, top_left, size)
