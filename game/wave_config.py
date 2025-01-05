# game/wave_config.py

WAVE_DURATION = 50  # 50초
SPAWN_DURATION = 40 # 40초 동안 유닛 1초마다
REST_DURATION = 10  # 10초 휴식

def get_stage_info(stage: int):
    """
    return dict of wave config
    e.g. stage=10 => boss spawn
    """
    is_boss = (stage % 10 == 0)
    return {
        "duration": WAVE_DURATION,
        "spawn_duration": SPAWN_DURATION,
        "rest_duration": REST_DURATION,
        "boss": is_boss,
    }
