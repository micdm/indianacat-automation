import logging.config
import os
from datetime import timedelta
from subprocess import call
from tempfile import TemporaryDirectory
from time import time, sleep
from typing import List, Tuple, Optional, Dict
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


def create_references() -> Dict[str, Image]:
    result = {}
    for root, dirs, files in os.walk('references'):
        for file in files:
            path = os.path.join(root, file)
            key = str(path.split('/', 1)[1]).rsplit('.', 1)[0]
            result[key] = create_image(path)
    return result


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

    def __init__(self, package_name: str, activity_name: str):
        self._package_name = package_name
        self._activity_name = activity_name

    def execute(self):
        logger.debug('Starting game')
        call([ADB, 'shell', 'am', 'start', '-n', '%s/%s' % (self._package_name, self._activity_name)])


class StopGameCommand(Command):

    def __init__(self, package_name: str):
        self._package_name = package_name

    def execute(self):
        logger.debug('Stopping game')
        call([ADB, 'shell', 'am', 'force-stop', self._package_name])


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

    def __init__(self, references: Dict[str, Image]):
        self._references = references

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
        return SimilarScreenshotCondition(self._references['common/power_off'], 0, 0, 2560, 1600)

    def get_command(self, stages: 'Stages') -> Command:
        return TogglePowerCommand()


class DesktopStage(Stage):

    def __init__(self, resources: Dict[str, Image], start_game_command: StartGameCommand):
        super().__init__(resources)
        self._start_game_command = start_game_command

    def get_condition(self) -> Condition:
        return SimilarScreenshotCondition(self._references['common/desktop'], 2470, 18, 82, 1570)

    def get_command(self, stages: 'Stages') -> Command:
        return self._start_game_command


class UnknownAdStage(Stage):

    def __init__(self, resources: Dict[str, Image], start_game_command: StartGameCommand):
        super().__init__(resources)
        self._start_game_command = start_game_command

    def get_condition(self) -> Condition:
        return AndCondition(
            SimilarScreenshotCondition(self._references['common/ad'], 998, 1520, 568, 73),
            SameScreenshotCondition()
        )

    def get_command(self, stages: 'Stages') -> Command:
        return self._start_game_command


class UnityAdStage(Stage):

    def __init__(self, resources: Dict[str, Image], start_game_command: StartGameCommand):
        super().__init__(resources)
        self._start_game_command = start_game_command

    def get_condition(self) -> Condition:
        return AndCondition(
            OrCondition(
                SimilarScreenshotCondition(self._references['common/ad_unity'], 2366, 636, 84, 302),
                SimilarScreenshotCondition(self._references['common/ad_unity_2'], 2388, 649, 74, 291)
            ),
            SameScreenshotCondition()
        )

    def get_command(self, stages: 'Stages') -> Command:
        return self._start_game_command


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


def handle_tick(stages_to_test: List[Stage], directory: str, screenshots: Screenshots,
                stages: Stages) -> Tuple[Screenshots, Stages, float]:
    now = time()
    path = grab_screenshot(directory)
    if not path:
        return screenshots, stages, TICK_INTERVAL
    screenshot = create_image(path)
    screenshots.add(path, screenshot)
    stage = get_current_stage(stages_to_test, screenshots, stages)
    if stage:
        logger.info('Stage now is %s', stage)
        stages.add(stage)
        stage.get_command(stages).execute()
        return screenshots, stages, TICK_INTERVAL
    logger.info('Unknown stage')
    return screenshots, stages, TICK_INTERVAL - (time() - now)


def run(stages_to_test):
    with TemporaryDirectory() as directory:
        logger.info('Using directory %s as storage', directory)
        screenshots = Screenshots(5)
        stages = Stages(20)
        while True:
            screenshots, stages, wait = handle_tick(stages_to_test, directory, screenshots, stages)
            if wait > 0:
                logger.debug('Sleeping for %.3f seconds', wait)
                sleep(wait)
