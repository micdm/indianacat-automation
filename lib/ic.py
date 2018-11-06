from datetime import timedelta
from typing import Dict, List

from PIL.Image import Image

from lib.common import Stage, Condition, AndCondition, SimilarScreenshotCondition, NotCondition, ClickCommand, \
    Command, BatchCommand, TogglePowerCommand, WaitCommand, StopGameCommand, UnknownAdStage, UnityAdStage, Stages, \
    PowerOffStage, DesktopStage, UnknownStage, StartGameCommand


class DailyBonusStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['ic/daily_bonus'], 800, 1060, 1030, 108),
            SimilarScreenshotCondition(self._references['ic/daily_bonus'], 2432, 1193, 82, 82)
        )

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(365, 2474)


class DailyBonusNotForFriendStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['ic/daily_bonus'], 800, 1060, 1030, 108),
            NotCondition(
                SimilarScreenshotCondition(self._references['ic/daily_bonus'], 2432, 1193, 82, 82)
            )
        )

    # TODO: залипает
    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(1142, 2433)


class DailyRewardStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/daily_reward'], 814, 478, 104, 654)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(774, 1624)


class StartBonusStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/start_bonus'], 503, 1363, 31, 112)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(131, 405)


class StartStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['ic/start'], 62, 929, 84, 84),
            NotCondition(
                SimilarScreenshotCondition(self._references['ic/start_bonus'], 503, 1363, 31, 112)
            )
        )

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(630, 120)


class BonusStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/bonus'], 48, 280, 188, 1294)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(800, 2362)


class BonusRewardStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/bonus_reward'], 898, 306, 114, 1000)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(784, 1538)


class BigLuckStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/big_luck'], 1012, 222, 662, 808)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(1414, 400)


class BankStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/bank'], 1806, 130, 286, 1336)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(800, 1900)


class BankTimerStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['ic/bank'], 386, 64, 144, 1472),
            NotCondition(
                SimilarScreenshotCondition(self._references['ic/bank'], 1806, 130, 286, 1336)
            )
        )

    def get_command(self, stages: Stages) -> Command:
        if isinstance(stages.previous, (UnknownAdStage, UnityAdStage)):
            return BatchCommand(
                TogglePowerCommand(),
                WaitCommand(timedelta(minutes=30))
            )
        if isinstance(stages.previous, StartStage):
            return BatchCommand(
                TogglePowerCommand(),
                WaitCommand(timedelta(minutes=10))
            )
        return ClickCommand(1478, 446)


class BankNoButtonStage(Stage):

    def __init__(self, resources: Dict[str, Image], stop_game_command: StopGameCommand):
        super().__init__(resources)
        self._stop_game_command = stop_game_command

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/bank_no_button'], 592, 62, 154, 1470)

    def get_command(self, stages: Stages) -> Command:
        return BatchCommand(
            self._stop_game_command,
            TogglePowerCommand(),
            WaitCommand(timedelta(minutes=10))
        )


class OfflineStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/offline'], 1031, 327, 355, 948)

    def get_command(self, stages: Stages) -> Command:
        return ClickCommand(800, 1430)


class VideoNotAvailableStage(Stage):

    def __init__(self, resources: Dict[str, Image], stop_game_command: StopGameCommand):
        super().__init__(resources)
        self._stop_game_command = stop_game_command

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['ic/video_not_available'], 1031, 327, 355, 948)

    def get_command(self, stages: Stages) -> Command:
        return BatchCommand(
            self._stop_game_command,
            TogglePowerCommand(),
            WaitCommand(timedelta(minutes=10))
        )


def get_stages_to_test(references: Dict[str, Image]) -> List[Stage]:
    package_name = 'com.playflock.indianacat'
    start_game_command = StartGameCommand(package_name, 'unity.pfplugins.com.activitybridge.UnityActivityOverrider')
    stop_game_command = StopGameCommand(package_name)
    return [
        PowerOffStage(references),
        DesktopStage(references, start_game_command),
        DailyBonusStage(references),
        DailyBonusNotForFriendStage(references),
        DailyRewardStage(references),
        StartBonusStage(references),
        StartStage(references),
        BonusStage(references),
        BonusRewardStage(references),
        BigLuckStage(references),
        BankStage(references),
        BankTimerStage(references),
        BankNoButtonStage(references, stop_game_command),
        OfflineStage(references),
        VideoNotAvailableStage(references, stop_game_command),
        UnknownAdStage(references, start_game_command),
        UnityAdStage(references, start_game_command),
        UnknownStage(references)
    ]
