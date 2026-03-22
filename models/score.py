import math


class ScoringSystem:
    def __init__(self, config: dict | None = None):
        self._load_config(config or {})
        self.reset()

    def _load_config(self, config: dict) -> None:
        self.base_multiplier = config.get("base_multiplier", 10.0)
        self.time_factor = config.get("time_factor", 0.001)
        self.top_speed_threshold = config.get("top_speed_threshold", 0.90)
        self.top_speed_bonus = config.get("top_speed_bonus", 50)
        self.accel_bonus_threshold = config.get("accel_bonus_threshold", 8.0)
        self.accel_bonus = config.get("accel_bonus", 25)
        self.combo_build_speed_ratio = config.get("combo_build_speed_ratio", 0.75)
        self.combo_max = config.get("combo_max", 5.0)
        self.combo_decay_rate = config.get("combo_decay_rate", 0.5)
        self.combo_reset_speed_ratio = config.get("combo_reset_speed_ratio", 0.4)
        self.combo_rise_rate = config.get("combo_rise_rate", 0.02)
        self.clean_drive_interval = config.get("clean_drive_interval", 5000)
        self.clean_drive_bonus = config.get("clean_drive_bonus", 100)
        self.near_miss_threshold = config.get("near_miss_threshold", 50)
        self.near_miss_bonus = config.get("near_miss_bonus", 75)
        self.sharp_turn_threshold = config.get("sharp_turn_threshold", 1.5)
        self.sharp_turn_bonus = config.get("sharp_turn_bonus", 40)
        self.difficulty_ramp_interval = config.get("difficulty_ramp_interval", 10000)
        self.difficulty_ramp_factor = config.get("difficulty_ramp_factor", 1.05)
        self.max_difficulty = config.get("max_difficulty", 3.0)
        self.score_soft_cap = config.get("score_soft_cap", 10000)
        self.soft_cap_diminish = config.get("soft_cap_diminish", 0.5)

    def reset(self) -> None:
        self.score = 0
        self._raw_score = 0.0
        self.combo = 1.0
        self.last_collision_time = 0
        self.last_high_speed_time = 0
        self.collision_free_time = 0
        self.last_clean_bonus_time = 0
        self.difficulty_multiplier = 1.0
        self.last_difficulty_increase = 0
        self.last_update_time = 0
        self.previous_speed = 0
        self.acceleration_history = []
        self._total_distance = 0.0
        self._near_miss_cooldown = 0
        self._sharp_turn_cooldown = 0

    def update(
        self,
        current_speed: float,
        max_speed: float,
        delta_time: float,
        steering: float,
        is_braking: bool,
        current_time: int,
        obstacles: list | None = None,
    ) -> dict:
        if delta_time <= 0 or is_braking:
            self._update_combo_decay(current_speed, max_speed, current_time)
            return self._get_status_dict()

        speed_ratio = max_speed > 0 and current_speed / max_speed or 0.0

        self._update_difficulty(current_time, delta_time)
        self._update_combo(speed_ratio, current_time, current_speed, max_speed)
        self._update_clean_drive_bonus(current_time, current_speed)

        base_points = self._calculate_base_points(speed_ratio, delta_time)
        difficulty_points = base_points * self.difficulty_multiplier
        combo_points = difficulty_points * self.combo

        top_speed_bonus = self._calculate_top_speed_bonus(
            speed_ratio, current_speed, max_speed
        )
        accel_bonus = self._calculate_acceleration_bonus(current_speed, delta_time)
        clean_bonus = self._get_clean_drive_pending(current_time)
        near_miss_bonus = self._calculate_near_miss_bonus(obstacles, current_time)
        sharp_turn_bonus = self._calculate_sharp_turn_bonus(steering, current_speed)

        total_points = (
            combo_points
            + top_speed_bonus
            + accel_bonus
            + clean_bonus
            + near_miss_bonus
            + sharp_turn_bonus
        )

        capped_points = self._apply_soft_cap(total_points)
        self._raw_score += capped_points
        self.score = int(self._raw_score)

        self._total_distance += current_speed * delta_time / 1000.0
        self.previous_speed = current_speed
        self.last_update_time = current_time

        return self._get_status_dict(
            base_points=base_points,
            difficulty_multiplier=self.difficulty_multiplier,
            combo=self.combo,
            top_speed_bonus=top_speed_bonus,
            accel_bonus=accel_bonus,
            clean_bonus=clean_bonus,
            near_miss_bonus=near_miss_bonus,
            sharp_turn_bonus=sharp_turn_bonus,
            total_points=capped_points,
        )

    def _calculate_base_points(self, speed_ratio: float, delta_time: float) -> float:
        normalized = max(0.0, min(1.0, speed_ratio))
        return normalized * self.base_multiplier * (delta_time * self.time_factor)

    def _calculate_top_speed_bonus(
        self, speed_ratio: float, current_speed: float, max_speed: float
    ) -> float:
        if speed_ratio >= self.top_speed_threshold and current_speed > 0:
            return self.top_speed_bonus * (speed_ratio - self.top_speed_threshold + 0.1)
        return 0.0

    def _calculate_acceleration_bonus(
        self, current_speed: float, delta_time: float
    ) -> float:
        if delta_time <= 0:
            return 0.0

        self.acceleration_history.append(current_speed)
        if len(self.acceleration_history) > 10:
            self.acceleration_history.pop(0)

        if len(self.acceleration_history) >= 2:
            recent_accel = (current_speed - self.acceleration_history[0]) / (
                len(self.acceleration_history) * delta_time / 1000.0
            )
            if recent_accel >= self.accel_bonus_threshold:
                return self.accel_bonus * (recent_accel / 20.0)

        return 0.0

    def _update_combo(
        self,
        speed_ratio: float,
        current_time: int,
        current_speed: float,
        max_speed: float,
    ) -> None:
        if speed_ratio >= self.combo_build_speed_ratio:
            self.combo = min(self.combo_max, self.combo + self.combo_rise_rate)
            self.last_high_speed_time = current_time
        elif speed_ratio < self.combo_reset_speed_ratio:
            self.combo = max(1.0, self.combo - self.combo_decay_rate * 0.1)

    def _update_combo_decay(
        self, current_speed: float, max_speed: float, current_time: int
    ) -> None:
        speed_ratio = max_speed > 0 and current_speed / max_speed or 0.0
        if speed_ratio < self.combo_reset_speed_ratio:
            decay_factor = self.combo_decay_rate * 0.05
            self.combo = max(1.0, self.combo - decay_factor)

    def _update_clean_drive_bonus(
        self, current_time: int, current_speed: float
    ) -> None:
        if current_speed > 0:
            self.collision_free_time += current_time - self.last_update_time
        else:
            self.collision_free_time = 0

    def _get_clean_drive_pending(self, current_time: int) -> float:
        if (
            self.collision_free_time >= self.clean_drive_interval
            and current_time - self.last_clean_bonus_time >= self.clean_drive_interval
        ):
            self.last_clean_bonus_time = current_time
            self.collision_free_time = 0
            return self.clean_drive_bonus
        return 0.0

    def _calculate_near_miss_bonus(
        self, obstacles: list | None, current_time: int
    ) -> float:
        if not obstacles or current_time < self._near_miss_cooldown:
            return 0.0

        self._near_miss_cooldown = current_time + 500
        return self.near_miss_bonus

    def _calculate_sharp_turn_bonus(
        self, steering: float, current_speed: float
    ) -> float:
        if current_time := self.last_update_time:
            if self._sharp_turn_cooldown > current_time:
                return 0.0

        if abs(steering) >= self.sharp_turn_threshold and current_speed > 10:
            self._sharp_turn_cooldown = (
                self.last_update_time + 300 if self.last_update_time else 0
            )
            return self.sharp_turn_bonus * abs(steering)
        return 0.0

    def _update_difficulty(self, current_time: int, delta_time: float) -> None:
        if (
            current_time - self.last_difficulty_increase
            >= self.difficulty_ramp_interval
        ):
            self.difficulty_multiplier = min(
                self.max_difficulty,
                self.difficulty_multiplier * self.difficulty_ramp_factor,
            )
            self.last_difficulty_increase = current_time

    def _apply_soft_cap(self, points: float) -> float:
        if self._raw_score >= self.score_soft_cap:
            excess = self._raw_score - self.score_soft_cap
            diminishing = 1.0 / (
                1.0 + excess * self.soft_cap_diminish / self.score_soft_cap
            )
            return points * diminishing
        return points

    def register_collision(self, current_time: int) -> None:
        self.combo = 1.0
        self.collision_free_time = 0
        self.last_collision_time = current_time
        self._near_miss_cooldown = current_time + 1000

    def register_near_miss(self, current_time: int) -> float:
        self._near_miss_cooldown = current_time + 200
        return self.near_miss_bonus

    def get_score(self) -> int:
        return self.score

    def get_raw_score(self) -> float:
        return self._raw_score

    def get_combo(self) -> float:
        return self.combo

    def get_difficulty(self) -> float:
        return self.difficulty_multiplier

    def get_distance(self) -> float:
        return self._total_distance

    def add_score(self, points: int) -> None:
        self._raw_score = max(0, self._raw_score + points)
        self.score = int(self._raw_score)

    def deduct(self, points: int) -> None:
        self._raw_score = max(0, self._raw_score - points)
        self.score = int(self._raw_score)

    def set_score(self, score: int) -> None:
        self._raw_score = max(0.0, float(score))
        self.score = max(0, score)

    def _get_status_dict(self, **kwargs) -> dict:
        return {
            "score": self.score,
            "combo": self.combo,
            "difficulty": self.difficulty_multiplier,
            "distance": self._total_distance,
            **kwargs,
        }

    def get_status(self) -> dict:
        return self._get_status_dict()


class Score:
    def __init__(self):
        self.score = 0

    def add_score(self, score):
        self.score = max(0, self.score + int(score))

    def deduct(self, deduct):
        self.score = max(0, self.score - int(deduct))

    def get_score(self):
        return self.score

    def set_score(self, score):
        self.score = max(0, int(score))

    def reset_score(self):
        self.score = 0
