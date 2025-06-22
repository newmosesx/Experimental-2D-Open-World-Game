import math
# Working on it


# Performance Based System
class Leveling():
    def __init__(self):
        # --- Core Constants ---
        self.LEVEL_DIFF_MODIFIER_PER_LEVEL = 0.10 # For base reward on win
        self.MAX_LEVEL_MODIFIER = 2.0
        self.MIN_LEVEL_MODIFIER = 0.1

        # --- Action Modifiers (% of potential BASE EXP reward) ---
        self.PLAYER_HIT_BONUS_PCT = 0.05
        self.PLAYER_DODGE_BONUS_PCT = 0.03
        self.PLAYER_BLOCK_BONUS_PCT = 0.01
        self.ENEMY_HIT_PENALTY_PCT = 0.03
        self.ENEMY_DODGE_PENALTY_PCT = 0.02
        self.ENEMY_BLOCK_PENALTY_PCT = 0.01

        # --- Difficulty Tiers & Performance Scaling ---
        # Defines multipliers applied to performance bonuses/penalties based on level diff
        # Key: (min_level_diff, max_level_diff) -> inclusive range
        # Value: performance_multiplier
        self.DIFFICULTY_PERFORMANCE_SCALES = {
            (-float('inf'), -1): 0.75,  # Easy: Lower bonus scaling, HIGHER penalty scaling
            (0, 3):            1.00,  # On Par: Baseline performance impact
            (4, 7):            1.25,  # Moderate: Higher bonus scaling, slightly lower penalty scaling
            (8, 11):           1.50,  # Hard: Significant bonus scaling, lower penalty scaling
            (12, float('inf')): 2.00   # Impossible: Extreme bonus scaling, lowest penalty scaling
        }
        # You can tune these multipliers extensively!

        # --- Experience Loss Cap ---
        self.MIN_EXP_CHANGE_PER_ENCOUNTER = -1000 # Still applies overall

    def _get_difficulty_performance_multiplier(self, level_difference: int) -> float:
        """Gets the performance scaling multiplier based on level difference."""
        for (min_diff, max_diff), multiplier in self.DIFFICULTY_PERFORMANCE_SCALES.items():
            if min_diff <= level_difference <= max_diff:
                return multiplier
        return 1.0 # Default fallback, should not happen with current ranges

    def calculate_exp_change(self,
                             # Player Section
                             player_level: int,
                             player_hit_count: int,
                             player_dodge_count: int,
                             player_block_count: int,

                             # Enemy Section
                             enemy_level: int,
                             enemy_hit_on_player_count: int,
                             enemy_dodge_against_player_count: int,
                             enemy_block_against_player_count: int,
                             base_exp_reward: int,

                             # Outcome
                             enemy_defeated: bool
                            ) -> int:
        """
        Calculates the net change in player EXP after an encounter, factoring in
        difficulty-based performance scaling. Penalties are scaled inversely
        to bonuses based on difficulty.

        Args:
            (Same as before)

        Returns:
            The integer amount of EXP change (can be positive or negative).
        """

        # 1. Calculate Level Difference & Base Reward Modifier
        level_difference = enemy_level - player_level
        level_modifier = 1.0 + (level_difference * self.LEVEL_DIFF_MODIFIER_PER_LEVEL)
        level_modifier = max(self.MIN_LEVEL_MODIFIER,
                             min(level_modifier, self.MAX_LEVEL_MODIFIER))

        # 2. Calculate Base Victory Reward Component (Only if won)
        victory_exp = 0
        if enemy_defeated:
            # Base reward is still modified by level difference for winning
            victory_exp = base_exp_reward * level_modifier

        # 3. Determine Difficulty Performance Multiplier
        difficulty_perf_multiplier = self._get_difficulty_performance_multiplier(level_difference)

        # 4. Calculate RAW Performance Bonus (based on player actions)
        raw_hit_bonus = player_hit_count * (base_exp_reward * self.PLAYER_HIT_BONUS_PCT)
        raw_dodge_bonus = player_dodge_count * (base_exp_reward * self.PLAYER_DODGE_BONUS_PCT)
        raw_block_bonus = player_block_count * (base_exp_reward * self.PLAYER_BLOCK_BONUS_PCT)
        raw_total_performance_bonus = raw_hit_bonus + raw_dodge_bonus + raw_block_bonus

        # 5. Calculate RAW Performance Penalty (based on enemy actions)
        raw_hit_penalty = enemy_hit_on_player_count * (base_exp_reward * self.ENEMY_HIT_PENALTY_PCT)
        raw_dodge_penalty = enemy_dodge_against_player_count * (base_exp_reward * self.ENEMY_DODGE_PENALTY_PCT)
        raw_block_penalty = enemy_block_against_player_count * (base_exp_reward * self.ENEMY_BLOCK_PENALTY_PCT)
        raw_total_performance_penalty = raw_hit_penalty + raw_dodge_penalty + raw_block_penalty

        # 6. Calculate Net Raw Performance & Apply Difficulty Scaling Differently
        net_raw_performance = raw_total_performance_bonus - raw_total_performance_penalty
        scaled_net_performance_component = 0

        if net_raw_performance >= 0:
            # Good performance: Scale bonus UP with difficulty multiplier
            scaled_net_performance_component = net_raw_performance * difficulty_perf_multiplier
            # print(f" Scaling Net POSITIVE Performance: {net_raw_performance:.2f} * {difficulty_perf_multiplier:.2f} = {scaled_net_performance_component:.2f}")
        else:
            # Poor performance: Scale penalty DOWN with difficulty multiplier (i.e., divide by it)
            # This makes penalties LARGER for easy fights (mult < 1) and SMALLER for hard fights (mult > 1)
            if difficulty_perf_multiplier > 1e-6: # Avoid division by zero or near-zero
                 scaled_net_performance_component = net_raw_performance / difficulty_perf_multiplier
                 # print(f" Scaling Net NEGATIVE Performance: {net_raw_performance:.2f} / {difficulty_perf_multiplier:.2f} = {scaled_net_performance_component:.2f}")
            else:
                 scaled_net_performance_component = net_raw_performance # Fallback if multiplier is zero/tiny

        # 7. Calculate Net Change
        # Start with scaled performance component, then add victory bonus if applicable
        net_exp_change = scaled_net_performance_component
        if enemy_defeated:
            net_exp_change += victory_exp

        # 8. Apply Minimum EXP Change Cap (Loss Cap)
        final_exp_change = max(net_exp_change, self.MIN_EXP_CHANGE_PER_ENCOUNTER)

        # Debug Print (Optional)
        # print(f"\n--- Calculation Details ---")
        # print(f" Player Lvl: {player_level}, Enemy Lvl: {enemy_level}, Base Reward: {base_exp_reward}")
        # print(f" LvlDiff: {level_difference}, LvlMod: {level_modifier:.2f}, DifficultyMult: {difficulty_perf_multiplier:.2f}")
        # print(f" Raw Bonus: {raw_total_performance_bonus:.2f}, Raw Penalty: {raw_total_performance_penalty:.2f}")
        # print(f" Net Raw Perf: {net_raw_performance:.2f}")
        # print(f" Scaled Perf Comp: {scaled_net_performance_component:.2f}")
        # print(f" Victory EXP: {victory_exp:.2f} (Only if won)")
        # print(f" Net (Pre-Cap): {net_exp_change:.2f}, Final: {math.floor(final_exp_change)}")
        # print("-" * 25)


        return math.floor(final_exp_change)

# --- Example Usage ---
leveling_system = Leveling()

print("--- Previous Scenarios (Check if behaviour is consistent where expected) ---")
# Scenario 1 (Win): Player (Lvl 10) vs Enemy (Lvl 12) -> diff=2 (On Par, mult=1.0)
exp_change1 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=15, player_dodge_count=5, player_block_count=2,
    enemy_level=12, enemy_hit_on_player_count=3, enemy_dodge_against_player_count=2, enemy_block_against_player_count=1,
    base_exp_reward=500, enemy_defeated=True
)
# Net Raw Perf = (15*25 + 5*15 + 2*5) - (3*15 + 2*10 + 1*5) = (375+75+10) - (45+20+5) = 460 - 70 = 390
# Scaled Perf = 390 * 1.0 = 390
# Lvl Mod = 1.0 + 2*0.1 = 1.2
# Victory EXP = 500 * 1.2 = 600
# Total = 390 + 600 = 990. Expected: 990 (Consistent)
print(f"Scenario 1 (Win, On Par) EXP Change: {exp_change1}")

# Scenario 2 (Loss/Flee): Player (Lvl 10) vs Enemy (Lvl 12) -> diff=2 (On Par, mult=1.0)
exp_change2 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=8, player_dodge_count=3, player_block_count=1,
    enemy_level=12, enemy_hit_on_player_count=5, enemy_dodge_against_player_count=4, enemy_block_against_player_count=2,
    base_exp_reward=500, enemy_defeated=False
)
# Net Raw Perf = (8*25 + 3*15 + 1*5) - (5*15 + 4*10 + 2*5) = (200+45+5) - (75+40+10) = 250 - 125 = 125
# Scaled Perf = 125 * 1.0 = 125
# Victory EXP = 0
# Total = 125. Expected: 125 (Consistent)
print(f"Scenario 2 (Loss, On Par) EXP Change: {exp_change2}")

# Scenario 3 (Loss/Flee): Player (Lvl 10) vs Enemy (Lvl 10) -> diff=0 (On Par, mult=1.0)
exp_change3 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=1, player_dodge_count=0, player_block_count=0,
    enemy_level=10, enemy_hit_on_player_count=15, enemy_dodge_against_player_count=5, enemy_block_against_player_count=3,
    base_exp_reward=300, enemy_defeated=False
)
# Net Raw Perf = (1*15 + 0*9 + 0*3) - (15*9 + 5*6 + 3*3) = 15 - (135 + 30 + 9) = 15 - 174 = -159
# Scaled Perf = -159 / 1.0 = -159
# Victory EXP = 0
# Total = -159. Expected: -159 (Consistent)
print(f"Scenario 3 (Loss, On Par - Poor Perf) EXP Change: {exp_change3}")

# Scenario 4 (Loss/Flee): Player (Lvl 5) vs Enemy (Lvl 20) -> diff=15 (Impossible, mult=2.0)
exp_change4 = leveling_system.calculate_exp_change(
    player_level=5, player_hit_count=2, player_dodge_count=1, player_block_count=0,
    enemy_level=20, enemy_hit_on_player_count=30, enemy_dodge_against_player_count=10, enemy_block_against_player_count=5,
    base_exp_reward=1000, enemy_defeated=False
)
# Net Raw Perf = (2*50 + 1*30 + 0*10) - (30*30 + 10*20 + 5*10) = (100+30) - (900+200+50) = 130 - 1150 = -1020
# Scaled Perf = -1020 / 2.0 = -510  <- **CHANGED BEHAVIOR** (Loss is LESS severe due to high difficulty)
# Victory EXP = 0
# Total = -510. Cap: max(-510, -500) = -500
print(f"Scenario 4 (Loss, Impossible - Hits Cap) EXP Change: {exp_change4}") # Expected: -500 (Hits cap, penalty reduced from -1020 to -510 before cap)

print("\n--- New Scenarios (Showcasing Difficulty Scaling - UPDATED LOGIC) ---")

# Scenario 5 (Win): Player (Lvl 10) vs Enemy (Lvl 15) -> diff=5 (Moderate, mult=1.25)
# Good performance against a moderately tougher enemy
exp_change5 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=12, player_dodge_count=4, player_block_count=3, # Good performance
    enemy_level=15, enemy_hit_on_player_count=4, enemy_dodge_against_player_count=3, enemy_block_against_player_count=2,
    base_exp_reward=700, enemy_defeated=True
)
# Level Mod: 1.0 + (5 * 0.1) = 1.5
# Victory EXP: 700 * 1.5 = 1050
# Raw Bonus: (12*700*0.05) + (4*700*0.03) + (3*700*0.01) = 420 + 84 + 21 = 525
# Raw Penalty: (4*700*0.03) + (3*700*0.02) + (2*700*0.01) = 84 + 42 + 14 = 140
# Net Raw Perf = 525 - 140 = 385 (Positive)
# Scaled Perf = 385 * 1.25 = 481.25
# Net: 481.25 + 1050 = 1531.25
# Floor: 1531
# Cap: max(1531, -500) = 1531
print(f"Scenario 5 (Win, Moderate Difficulty) EXP Change: {exp_change5}") # Expected: 1531 (Same as before, positive performance scales normally)

# Scenario 6 (Loss): Player (Lvl 10) vs Enemy (Lvl 7) -> diff=-3 (Easy, mult=0.75)
# Poor performance and loss against an easier enemy
exp_change6 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=5, player_dodge_count=1, player_block_count=0, # Poor performance
    enemy_level=7, enemy_hit_on_player_count=10, enemy_dodge_against_player_count=5, enemy_block_against_player_count=4, # Took many hits
    base_exp_reward=200, enemy_defeated=False
)
# Victory EXP: 0
# Raw Bonus: (5*200*0.05) + (1*200*0.03) + 0 = 50 + 6 = 56
# Raw Penalty: (10*200*0.03) + (5*200*0.02) + (4*200*0.01) = 60 + 20 + 8 = 88
# Net Raw Perf = 56 - 88 = -32 (Negative)
# Scaled Perf = -32 / 0.75 = -42.66... <- **CHANGED BEHAVIOR** (Loss is MORE severe due to easy difficulty)
# Net: -42.66...
# Floor: -43
# Cap: max(-43, -500) = -43
print(f"Scenario 6 (Loss, Easy Difficulty - Poor Perf) EXP Change: {exp_change6}") # Expected: -43 (Loss increased from -32 to -43 because it was an easy fight)

# Scenario 7 (Win): Player (Lvl 5) vs Enemy (Lvl 16) -> diff=11 (Hard, mult=1.5)
# Average performance, but win against hard enemy
exp_change7 = leveling_system.calculate_exp_change(
    player_level=5, player_hit_count=8, player_dodge_count=2, player_block_count=1,
    enemy_level=16, enemy_hit_on_player_count=6, enemy_dodge_against_player_count=4, enemy_block_against_player_count=3,
    base_exp_reward=900, enemy_defeated=True
)
# Level Mod: 1.0 + (11 * 0.1) = 2.1 -> Clamped to 2.0
# Victory EXP: 900 * 2.0 = 1800
# Raw Bonus: (8*900*0.05) + (2*900*0.03) + (1*900*0.01) = 360 + 54 + 9 = 423
# Raw Penalty: (6*900*0.03) + (4*900*0.02) + (3*900*0.01) = 162 + 72 + 27 = 261
# Net Raw Perf = 423 - 261 = 162 (Positive)
# Scaled Perf = 162 * 1.5 = 243
# Net: 243 + 1800 = 2043
# Floor: 2043
# Cap: max(2043, -500) = 2043
print(f"Scenario 7 (Win, Hard Difficulty) EXP Change: {exp_change7}") # Expected: 2043 (Same as before, positive performance scales normally)

print("\n--- Additional Scenarios (Focus on Poor Performance Scaling) ---")

# Scenario 8 (Loss): Player (Lvl 10) vs Enemy (Lvl 18) -> diff=8 (Hard, mult=1.5)
# Poor performance against a hard enemy
exp_change8 = leveling_system.calculate_exp_change(
    player_level=10, player_hit_count=3, player_dodge_count=1, player_block_count=0, # Poor performance
    enemy_level=18, enemy_hit_on_player_count=12, enemy_dodge_against_player_count=6, enemy_block_against_player_count=4,
    base_exp_reward=800, enemy_defeated=False
)
# Raw Bonus: (3*800*0.05) + (1*800*0.03) + 0 = 120 + 24 = 144
# Raw Penalty: (12*800*0.03) + (6*800*0.02) + (4*800*0.01) = 288 + 96 + 32 = 416
# Net Raw Perf = 144 - 416 = -272 (Negative)
# Scaled Perf = -272 / 1.5 = -181.33... <- Penalty Reduced
# Net: -181.33...
# Floor: -182
# Cap: max(-182, -500) = -182
print(f"Scenario 8 (Loss, Hard Difficulty - Poor Perf) EXP Change: {exp_change8}") # Expected: -182 (Loss reduced from -272 to -182 due to hard difficulty)


# Scenario 9 (Loss): Player (Lvl 15) vs Enemy (Lvl 10) -> diff=-5 (Easy, mult=0.75)
# Very poor performance against an easy enemy
exp_change9 = leveling_system.calculate_exp_change(
    player_level=15, player_hit_count=2, player_dodge_count=0, player_block_count=0, # Very poor performance
    enemy_level=10, enemy_hit_on_player_count=10, enemy_dodge_against_player_count=8, enemy_block_against_player_count=5,
    base_exp_reward=300, enemy_defeated=False
)
# Raw Bonus: (2*300*0.05) + 0 + 0 = 30
# Raw Penalty: (10*300*0.03) + (8*300*0.02) + (5*300*0.01) = 90 + 48 + 15 = 153
# Net Raw Perf = 30 - 153 = -123 (Negative)
# Scaled Perf = -123 / 0.75 = -164 <- Penalty Increased
# Net: -164
# Floor: -164
# Cap: max(-164, -500) = -164
print(f"Scenario 9 (Loss, Easy Difficulty - Very Poor Perf) EXP Change: {exp_change9}") # Expected: -164 (Loss increased from -123 to -164 due to easy difficulty)