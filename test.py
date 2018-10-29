import os
from random import randint
from typing import List

import pytest
from PIL.Image import Image, frombytes

from main import SimilarScreenshotCondition, grab_screenshot, get_actual_screenshots, \
    SCREENSHOTS_TO_START, get_current_stage, STAGES, NotCondition, Condition, AndCondition, OrCondition, \
    SameScreenshotCondition


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


@pytest.fixture
def image3_path(tmp_path):
    return tmp_path / 'image3.png'


@pytest.fixture
def image3(image3_path):
    return create_random_content_image(image3_path)


def create_random_content_image(path: str) -> Image:
    array = bytes(randint(0, 255) for _ in range(100 * 100 * 3))
    image = frombytes('RGB', (100, 100), array)
    image.save(path)
    return image


@pytest.fixture
def true_condition():
    class TrueCondition(Condition):
        def is_met(self, screenshot: Image, prev_screenshots: List[Image], stage, prev_stage) -> bool:
            return True

    return TrueCondition()


@pytest.fixture
def false_condition():
    class FalseCondition(Condition):
        def is_met(self, screenshot: Image, prev_screenshots: List[Image], stage, prev_stage) -> bool:
            return False

    return FalseCondition()


def test_not_condition(true_condition):
    result = NotCondition(true_condition).is_met(None, None, None, None)
    assert not result


def test_and_condition(true_condition, false_condition):
    result = AndCondition(true_condition, false_condition).is_met(None, None, None, None)
    assert not result


def test_or_condition(true_condition, false_condition):
    result = OrCondition(true_condition, false_condition).is_met(None, None, None, None)
    assert result


def test_similar_screenshot_condition(image1, image2):
    result = SimilarScreenshotCondition(image1, 0, 0, image1.width, image1.height).is_met(image1, [], None, None)
    assert result
    result = SimilarScreenshotCondition(image1, 0, 0, image1.width, image1.height).is_met(image2, [], None, None)
    assert not result


def test_same_screenshot_condition(image1, image2):
    result = SameScreenshotCondition().is_met(image1, [image1], None, None)
    assert result
    result = SameScreenshotCondition().is_met(image1, [image2], None, None)
    assert not result


@pytest.mark.skip(reason='device required')
def test_grab_screenshot(temp_directory):
    with temp_directory as path:
        result = grab_screenshot(path)
        assert result.startswith(path)
        assert result.endswith('.png')


def test_get_actual_screenshots_if_not_enough(image1_path, image1):
    result = get_actual_screenshots([(image1_path, image1)])
    assert result is None


def test_get_actual_screenshots_if_enough(mocker, image1_path, image1, image2_path, image2, image3_path, image3):
    mocker.patch.object(os, 'remove')
    result = get_actual_screenshots([
        (image1_path, image1),
        (image2_path, image2),
        (image3_path, image3),
    ])
    assert len(result) == SCREENSHOTS_TO_START
    assert os.remove.call_args == ((image3_path,),)


def test_get_current_stage_if_not_met(image1, image2):
    result = get_current_stage(STAGES, image1, [image2], None)
    assert result is None


def test_get_current_stage_if_met(mocker, image1, image2):
    stage = mocker.Mock()
    stage.get_condition().is_met.return_value = True
    result = get_current_stage([stage], image1, [image2], None)
    assert result == stage
