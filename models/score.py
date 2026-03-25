class ScoringSystem:
    def __init__(self, config: dict | None = None):
        self._load_config(config or {})
        self.reset()

    def _load_config(self, config: dict) -> None:
        self.base_points_per_second = config.get("base_points_per_second", 8.33)
        self.top_speed_threshold = config.get("top_speed_threshold", 0.90)
        self.top_speed_bonus = config.get("top_speed_bonus", 10)
        self.accel_bonus_threshold = config.get("accel_bonus_threshold", 8.0)
        self.accel_bonus = config.get("accel_bonus", 5)
        self.clean_drive_interval = config.get("clean_drive_interval", 10000)
        self.clean_drive_bonus = config.get("clean_drive_bonus", 50)
        self.near_miss_bonus = config.get("near_miss_bonus", 25)
        self.sharp_turn_threshold = config.get("sharp_turn_threshold", 1.5)
        self.sharp_turn_bonus = config.get("sharp_turn_bonus", 10)
        self.difficulty_ramp_interval = config.get("difficulty_ramp_interval", 60000)
        self.difficulty_ramp_factor = config.get("difficulty_ramp_factor", 1.10)
        self.max_difficulty = config.get("max_difficulty", 2.0)

    def reset(self) -> None:
        self.score = 0
        self._raw_score = 0.0
        self.last_collision_time = 0
        self.collision_free_time = 0
        self.last_clean_bonus_time = 0
        self.difficulty_multiplier = 1.0
        self.last_difficulty_increase = 0
        self.last_update_time = 0
        self.previous_speed = 0
        self._recent_accel = 0.0
        self._total_distance = 0.0
        self._near_miss_cooldown = 0
        self._sharp_turn_cooldown = 0
        self._bonus_timer = 0

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
        if delta_time <= 0:
            return self._get_status_dict()

        speed_ratio = current_speed / max_speed if max_speed > 0 else 0.0
        self._update_difficulty(current_time)
        self._update_clean_drive(current_time, current_speed)

        if not is_braking:
            base_points = (
                self.base_points_per_second
                * (delta_time / 1000.0)
                * speed_ratio
                * self.difficulty_multiplier
            )
        else:
            base_points = (
                self.base_points_per_second
                * 0.3
                * (delta_time / 1000.0)
                * speed_ratio
                * self.difficulty_multiplier
            )

        top_speed_bonus = 0.0
        if speed_ratio >= self.top_speed_threshold and current_speed > 0:
            self._bonus_timer += delta_time
            if self._bonus_timer >= 1000:
                top_speed_bonus = self.top_speed_bonus
                self._bonus_timer = 0
        else:
            self._bonus_timer = 0

        accel_bonus = 0.0
        if delta_time > 0 and not is_braking:
            self._recent_accel = (current_speed - self.previous_speed) / (
                delta_time / 1000.0
            )
            if self._recent_accel >= self.accel_bonus_threshold:
                accel_bonus = self.accel_bonus * min(1.0, self._recent_accel / 20.0)

        clean_bonus = 0.0
        if (
            self.collision_free_time >= self.clean_drive_interval
            and current_time - self.last_clean_bonus_time >= self.clean_drive_interval
        ):
            self.last_clean_bonus_time = current_time
            self.collision_free_time = 0
            clean_bonus = self.clean_drive_bonus

        near_miss_bonus = 0.0
        if obstacles and current_time >= self._near_miss_cooldown:
            self._near_miss_cooldown = current_time + 500
            near_miss_bonus = self.near_miss_bonus

        sharp_turn_bonus = 0.0
        if current_time >= self._sharp_turn_cooldown:
            if abs(steering) >= self.sharp_turn_threshold and current_speed > 10:
                self._sharp_turn_cooldown = current_time + 300
                sharp_turn_bonus = self.sharp_turn_bonus * abs(steering)

        total_points = (
            base_points
            + top_speed_bonus
            + accel_bonus
            + clean_bonus
            + near_miss_bonus
            + sharp_turn_bonus
        )
        self._raw_score += total_points
        self.score = int(self._raw_score)

        self._total_distance += current_speed * delta_time / 1000.0
        self.previous_speed = current_speed
        self.last_update_time = current_time

        return self._get_status_dict()

    def _update_clean_drive(self, current_time: int, current_speed: float) -> None:
        if current_speed > 0:
            elapsed = (
                current_time - self.last_update_time if self.last_update_time > 0 else 0
            )
            self.collision_free_time += elapsed

    def _update_difficulty(self, current_time: int) -> None:
        if (
            current_time - self.last_difficulty_increase
            >= self.difficulty_ramp_interval
        ):
            self.difficulty_multiplier = min(
                self.max_difficulty,
                self.difficulty_multiplier * self.difficulty_ramp_factor,
            )
            self.last_difficulty_increase = current_time

    def register_collision(self, current_time: int) -> None:
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
        return 1.0

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

    def _get_status_dict(self) -> dict:
        return {
            "score": self.score,
            "difficulty": self.difficulty_multiplier,
            "distance": self._total_distance,
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
