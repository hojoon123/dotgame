# game/management/commands/load_templates.py
from django.core.management.base import BaseCommand
from game.models import BallTemplate, EnemyTemplate

class Command(BaseCommand):
    help = "Load seed data into BallTemplate & EnemyTemplate"

    def handle(self, *args, **options):
        self.stdout.write("Loading seed data...")

        # 1) BallTemplate
        BallTemplate.objects.all().delete()

        # 간단히 7색 x 4등급 = 28종 예시
        color_list = ["red","orange","yellow","green","blue","navy","purple"]
        rarity_data = [
            ("common",    50,  3, 1.0, None),
            ("rare",      10,  5, 1.2, "burn"),
            ("epic",       5,  7, 1.3, "slow"),
            ("legendary",  1,  10,1.5, "drain"),
        ]
        for color in color_list:
            for (rarity, weight, dmg, spd, special) in rarity_data:
                BallTemplate.objects.create(
                    color=color,
                    rarity=rarity,
                    weight=weight,
                    base_damage=dmg,
                    base_attack_speed=spd,
                    special_option=special
                )
        self.stdout.write("Created BallTemplate records.")

        # 2) EnemyTemplate
        EnemyTemplate.objects.all().delete()

        # 예시: stage1~5 normal 적, stage5~10 hunt, stage10 boss
        EnemyTemplate.objects.create(name="Slime", enemy_type="normal", hp=10, defense=1, shield=0, stage_min=1, stage_max=5)
        EnemyTemplate.objects.create(name="Goblin", enemy_type="normal", hp=15, defense=2, shield=0, stage_min=1, stage_max=5)
        EnemyTemplate.objects.create(name="Wolf", enemy_type="hunt",   hp=25, defense=3, shield=2, stage_min=5, stage_max=10)
        EnemyTemplate.objects.create(name="Orc", enemy_type="hunt",    hp=35, defense=5, shield=5, stage_min=5, stage_max=10)
        EnemyTemplate.objects.create(name="Dragon", enemy_type="boss", hp=100, defense=10, shield=10, stage_min=10, stage_max=10)

        self.stdout.write("Created EnemyTemplate records.")

        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))
