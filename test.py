from random import randint

import pytest
from PIL.Image import Image, frombytes

from lib import common, ic, mlp
from lib.common import Screenshots, Stages, UnknownStage, TrueCondition, Condition, create_references, NotCondition, \
    AndCondition, OrCondition, SimilarScreenshotCondition, SameScreenshotCondition, grab_screenshot, get_current_stage
from lib.ic import StartStage


@pytest.fixture
def image1_path(tmp_path):
    return tmp_path / 'image1.png'


@pytest.fixture
def image1(image1_path):
    return create_random_content_image(image1_path)


@pytest.fixture
def image2_path(tmp_path):
    return tmp_path / 'image2.png'


@pytest.fixture
def image2(image2_path):
    return create_random_content_image(image2_path)


def create_random_content_image(path: str) -> Image:
    array = bytes(randint(0, 255) for _ in range(100 * 100 * 3))
    image = frombytes('RGB', (100, 100), array)
    image.save(path)
    return image


@pytest.fixture
def single_screenshot(image1):
    screenshots = Screenshots(1)
    screenshots.add('', image1)
    return screenshots


@pytest.fixture
def two_screenshots(image1, image2):
    screenshots = Screenshots(2)
    screenshots.add('', image1)
    screenshots.add('', image2)
    return screenshots


@pytest.fixture
def two_same_screenshots(image1):
    screenshots = Screenshots(2)
    screenshots.add('', image1)
    screenshots.add('', image1)
    return screenshots


@pytest.fixture
def stages():
    stages = Stages(2)
    stages.add(UnknownStage(None))
    stages.add(StartStage(None))
    return stages


@pytest.fixture
def true_condition():
    return TrueCondition()


@pytest.fixture
def false_condition():
    class _Condition(Condition):
        def is_met(self, screenshots: Image, stages) -> bool:
            return False
    return _Condition()


@pytest.fixture(scope='module')
def references():
    return create_references()


@pytest.fixture(scope='module')
def ic_stages_to_test(references):
    return ic.get_stages_to_test(references)


@pytest.fixture(scope='module')
def mlp_stages_to_test(references):
    return mlp.get_stages_to_test(references)


def test_create_references(references):
    assert len(references)
    first_key = list(references.keys())[0]
    assert not first_key.startswith('references/')
    assert not first_key.endswith('.png')


def test_true_condition(true_condition, single_screenshot, stages):
    result = true_condition.is_met(single_screenshot, stages)
    assert result


def test_not_condition(true_condition, single_screenshot, stages):
    result = NotCondition(true_condition).is_met(single_screenshot, stages)
    assert not result


def test_and_condition(true_condition, false_condition, single_screenshot, stages):
    result = AndCondition(true_condition, false_condition).is_met(single_screenshot, stages)
    assert not result


def test_or_condition(true_condition, false_condition, single_screenshot, stages):
    result = OrCondition(true_condition, false_condition).is_met(single_screenshot, stages)
    assert result


def test_similar_screenshot_condition(image1, image2, single_screenshot, stages):
    result = SimilarScreenshotCondition(image1, 0, 0, image1.width, image1.height).is_met(single_screenshot, stages)
    assert result
    result = SimilarScreenshotCondition(image2, 0, 0, image1.width, image1.height).is_met(single_screenshot, stages)
    assert not result


def test_same_screenshot_condition(single_screenshot, two_same_screenshots, two_screenshots, stages):
    result = SameScreenshotCondition().is_met(single_screenshot, stages)
    assert not result
    result = SameScreenshotCondition().is_met(two_same_screenshots, stages)
    assert result
    result = SameScreenshotCondition().is_met(two_screenshots, stages)
    assert not result


def test_ic_get_stages_to_test(ic_stages_to_test):
    for stage in ic_stages_to_test:
        assert stage.get_command(Stages(1)) is not None
    assert any(isinstance(stage, UnknownStage) for stage in ic_stages_to_test)


def test_mlp_get_stages_to_test(mlp_stages_to_test):
    for stage in mlp_stages_to_test:
        assert stage.get_command(Stages(1)) is not None
    assert any(isinstance(stage, UnknownStage) for stage in mlp_stages_to_test)


def test_screenshots(two_screenshots, image1, image2):
    assert two_screenshots.previous == image1
    assert two_screenshots.last == image2


def test_stages(stages):
    assert isinstance(stages.previous, UnknownStage)
    assert not stages.is_unknown_for_long_time


@pytest.mark.skip(reason='device required')
def test_grab_screenshot(tmp_path):
    path = str(tmp_path)
    result = grab_screenshot(path)
    assert result.startswith(path)
    assert result.endswith('.png')


def test_grab_screenshot_if_cannot_grab(mocker, tmp_path):
    mocker.patch.object(common, 'call')
    common.call.return_value = 1
    path = str(tmp_path)
    result = grab_screenshot(path)
    assert result is None


def test_get_current_stage_if_not_met(ic_stages_to_test, two_screenshots, stages):
    result = get_current_stage(ic_stages_to_test, two_screenshots, stages)
    assert isinstance(result, UnknownStage)


def test_get_current_stage_if_met(mocker, two_screenshots, stages):
    stage = mocker.Mock()
    stage.get_condition().is_met.return_value = True
    result = get_current_stage([stage], two_screenshots, stages)
    assert result == stage
