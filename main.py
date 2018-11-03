#!/usr/bin/env python3

import logging.config
import os
from datetime import timedelta
from subprocess import call
from tempfile import TemporaryDirectory
from time import time, sleep
from typing import List, Tuple, Optional
from uuid import uuid4

from PIL import ImageChops
from PIL.Image import Image, open as open_image

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s] %(message)s',
        }
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
        },
        'PIL': {
            'handlers': ['default'],
            'level': 'WARNING',
            'propagate': False,
        }
    }
})
logger = logging.getLogger(__name__)


ADB = '/opt/android-sdk/platform-tools/adb'
TICK_INTERVAL = 5


def create_image(path: str) -> Image:
    return open_image(path).convert('RGB')


REFERENCES = dict((name, create_image('references/%s.png' % name)) for name in (
    'ad', 'ad_unity', 'bank', 'bank_no_button', 'big_luck', 'bonus', 'daily_bonus', 'daily_reward', 'desktop',
    'offline', 'power_off', 'bonus_reward', 'start', 'start_bonus', 'video_not_available'
))


class Condition:

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        raise NotImplementedError()


class TrueCondition(Condition):

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        return True


class NotCondition(Condition):

    def __init__(self, condition: Condition):
        self._condition = condition

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        return not self._condition.is_met(screenshots, stages)


class AndCondition(Condition):

    def __init__(self, *conditions: Condition):
        self._conditions = conditions

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        return all(condition.is_met(screenshots, stages) for condition in self._conditions)


class OrCondition(Condition):

    def __init__(self, *conditions: Condition):
        self._conditions = conditions

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        return any(condition.is_met(screenshots, stages) for condition in self._conditions)


class SimilarScreenshotCondition(Condition):

    def __init__(self, reference: Image, left: int, top: int, width: int, height: int):
        self._reference = reference
        self._left = left
        self._top = top
        self._width = width
        self._height = height

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        area = (self._left, self._top, self._left + self._width, self._top + self._height)
        diff = ImageChops.difference(screenshots.last.crop(area), self._reference.crop(area))
        return not diff.getbbox()


class SameScreenshotCondition(Condition):

    def is_met(self, screenshots: 'Screenshots', stages: 'Stages') -> bool:
        if not screenshots.previous:
            return False
        diff = ImageChops.difference(screenshots.last, screenshots.previous)
        return not diff.getbbox()


class Command:

    def execute(self):
        raise NotImplementedError()


class NoOpCommand(Command):

    def execute(self):
        logger.debug('Doing nothing')


class BatchCommand(Command):

    def __init__(self, *commands: Command):
        self._commands = commands

    def execute(self):
        for command in self._commands:
            command.execute()


class StartGameCommand(Command):

    def execute(self):
        logger.debug('Starting game')
        call([ADB, 'shell', 'am', 'start', '-n',
              'com.playflock.indianacat/unity.pfplugins.com.activitybridge.UnityActivityOverrider'])


class StopGameCommand(Command):

    def execute(self):
        logger.debug('Stopping game')
        call([ADB, 'shell', 'am', 'force-stop', 'com.playflock.indianacat'])


class ClickCommand(Command):

    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    def execute(self):
        logger.debug('Clicking to (%s, %s)', self._x, self._y)
        call([ADB, 'shell', 'input', 'tap', str(self._x), str(self._y)])


class TogglePowerCommand(Command):

    def execute(self):
        logger.debug('Toggling device power')
        call([ADB, 'shell', 'input', 'keyevent', '26'])


class WaitCommand(Command):

    def __init__(self, duration: timedelta):
        self._duration = duration

    def execute(self):
        logger.debug('Waiting for %s', self._duration)
        sleep(self._duration.total_seconds())


class Stage:

    def __str__(self):
        return '%s()' % self.__class__.__name__

    def get_condition(self) -> Condition:
        raise NotImplementedError()

    def get_command(self, stages: 'Stages') -> Command:
        raise NotImplementedError()


class UnknownStage(Stage):

    def get_condition(self) -> Condition:
        return TrueCondition()

    def get_command(self, stages: 'Stages') -> Command:
        return NoOpCommand()


class PowerOffStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(create_image('references/power_off.png'), 0, 0, 2560, 1600)

    def get_command(self, stages: 'Stages') -> Command:
        return TogglePowerCommand()


class DesktopStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['desktop'], 2470, 18, 82, 1570)

    def get_command(self, stages: 'Stages') -> Command:
        return StartGameCommand()


class DailyBonusStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['daily_bonus'], 800, 1060, 1030, 108),
            SimilarScreenshotCondition(REFERENCES['daily_bonus'], 2432, 1193, 82, 82)
        )

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(365, 2474)


class DailyBonusNotForFriendStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['daily_bonus'], 800, 1060, 1030, 108),
            NotCondition(
                SimilarScreenshotCondition(REFERENCES['daily_bonus'], 2432, 1193, 82, 82)
            )
        )

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(1142, 2433)


class DailyRewardStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['daily_reward'], 814, 478, 104, 654)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(774, 1624)


class StartBonusStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['start_bonus'], 503, 1363, 31, 112)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(131, 405)


class StartStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['start'], 62, 929, 84, 84),
            NotCondition(
                SimilarScreenshotCondition(REFERENCES['start_bonus'], 503, 1363, 31, 112)
            )
        )

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(630, 120)


class BonusStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['bonus'], 48, 280, 188, 1294)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(800, 2362)


class BonusRewardStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['bonus_reward'], 898, 306, 114, 1000)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(784, 1538)


class BigLuckStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['big_luck'], 1012, 222, 662, 808)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(1414, 400)


class BankStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['bank'], 1806, 130, 286, 1336)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(800, 1900)


class BankTimerStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['bank'], 386, 64, 144, 1472),
            NotCondition(
                SimilarScreenshotCondition(REFERENCES['bank'], 1806, 130, 286, 1336)
            )
        )

    def get_command(self, stages: 'Stages') -> Command:
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

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['bank_no_button'], 592, 62, 154, 1470)

    def get_command(self, stages: 'Stages') -> Command:
        return BatchCommand(
            StopGameCommand(),
            TogglePowerCommand(),
            WaitCommand(timedelta(minutes=10))
        )


class OfflineStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['offline'], 1031, 327, 355, 948)

    def get_command(self, stages: 'Stages') -> Command:
        return ClickCommand(800, 1430)


class VideoNotAvailableStage(Stage):

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(REFERENCES['video_not_available'], 1031, 327, 355, 948)

    def get_command(self, stages: 'Stages') -> Command:
        return BatchCommand(
            StopGameCommand(),
            TogglePowerCommand(),
            WaitCommand(timedelta(minutes=10))
        )


class UnknownAdStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['ad'], 998, 1520, 568, 73),
            SameScreenshotCondition()
        )

    def get_command(self, stages: 'Stages') -> Command:
        return StartGameCommand()


class UnityAdStage(Stage):

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(REFERENCES['ad_unity'], 2366, 636, 84, 302),
            SameScreenshotCondition()
        )

    def get_command(self, stages: 'Stages') -> Command:
        return StartGameCommand()


STAGES = [PowerOffStage(), DesktopStage(), DailyBonusStage(), DailyBonusNotForFriendStage(), DailyRewardStage(),
          StartBonusStage(), StartStage(), BonusStage(), BonusRewardStage(), BigLuckStage(), BankStage(),
          BankTimerStage(), BankNoButtonStage(), OfflineStage(), VideoNotAvailableStage(), UnknownAdStage(),
          UnityAdStage(), UnknownStage()]


class Screenshots:

    def __init__(self, max_count: int):
        self._screenshots: Tuple[str, Image] = []
        self._max_count = max_count

    @property
    def last(self) -> Optional[Image]:
        return self._get_by_index(0)

    @property
    def previous(self) -> Optional[Image]:
        return self._get_by_index(1)

    def _get_by_index(self, index: int) -> Optional[Image]:
        try:
            return self._screenshots[index][1]
        except IndexError:
            return None

    def add(self, path: str, screenshot: Image):
        self._screenshots.insert(0, (path, screenshot))
        for path, _ in self._screenshots[self._max_count:]:
            logger.debug('Removing screenshot %s', path)
            os.remove(path)
        self._screenshots = self._screenshots[:self._max_count]


class Stages:

    def __init__(self, max_count: int):
        self._stages = []
        self._max_count = max_count

    @property
    def previous(self) -> Optional[Stage]:
        return self._get_by_index(1)

    def _get_by_index(self, index: int) -> Optional[Stage]:
        try:
            return self._stages[index]
        except IndexError:
            return None

    def add(self, stage: Stage):
        self._stages.insert(0, stage)
        self._stages = self._stages[:self._max_count]


def grab_screenshot(directory: str) -> Optional[str]:
    now = time()
    logger.debug('Grabbing screenshot')
    path = os.path.join(directory, '%s.png' % uuid4())
    if call(['./grab', path]):
        logger.warning('Cannot grab screenshot %s', path)
        return None
    logger.debug('Screenshot %s ready in %.3f seconds', path, time() - now)
    return path


def get_current_stage(stages_to_test: List[Stage], screenshots: Screenshots, stages: Stages) -> Optional[Stage]:
    for stage in stages_to_test:
        if stage.get_condition().is_met(screenshots, stages):
            return stage
    raise RuntimeError('stage not defined')


def handle_tick(directory: str, screenshots: Screenshots, stages: Stages) -> Tuple[Screenshots, Stages, float]:
    now = time()
    path = grab_screenshot(directory)
    if not path:
        return screenshots, stages, TICK_INTERVAL
    screenshot = create_image(path)
    screenshots.add(path, screenshot)
    stage = get_current_stage(STAGES, screenshots, stages)
    if stage:
        logger.info('Stage now is %s', stage)
        stages.add(stage)
        stage.get_command(stages).execute()
        return screenshots, stages, TICK_INTERVAL
    logger.info('Unknown stage')
    return screenshots, stages, TICK_INTERVAL - (time() - now)


def run():
    with TemporaryDirectory() as directory:
        logger.info('Using directory %s as storage', directory)
        screenshots = Screenshots(5)
        stages = Stages(20)
        while True:
            screenshots, stages, wait = handle_tick(directory, screenshots, stages)
            if wait > 0:
                logger.debug('Sleeping for %.3f seconds', wait)
                sleep(wait)


if __name__ == '__main__':
    run()
