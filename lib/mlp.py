from typing import Dict, List

from PIL.Image import Image

from lib.common import Stage, UnityAdStage, Command, Condition, SimilarScreenshotCondition, Stages, ClickCommand, \
    UnknownStage, StartGameCommand, AndCondition, OrCondition, SameScreenshotCondition


class NextEpisodeStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['mlp/next_episode'], 850, 478, 318, 624)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(640, 1530)


class InteractiveAdStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['mlp/interactive_ad'], 45, 45, 6, 6),
            SimilarScreenshotCondition(self._references['mlp/interactive_ad'], 2399, 1533, 7, 10)
        )

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(1552, 48)


class AnotherAdStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            OrCondition(
                SimilarScreenshotCondition(self._references['mlp/another_ad'], 146, 636, 80, 294),
                SimilarScreenshotCondition(self._references['mlp/another_ad_rotated'], 2332, 674, 84, 284)
            ),
            SameScreenshotCondition()
        )

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(1500, 90)


def get_stages_to_test(references: Dict[str, Image]) -> List[Stage]:
    start_game_command = StartGameCommand('com.nevosoft.mylittleplanet', '.Main')
    return [
        NextEpisodeStage(references),
        InteractiveAdStage(references),
        AnotherAdStage(references),
        UnityAdStage(references, start_game_command),
        UnknownStage(references)
    ]
