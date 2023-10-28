import pytest

from chat2func.utils import approx_token_count


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("the quick brown fox jumped over the yellow dog!", 10),
        (
            "Reinforcement Learning from Human Feedback (RLHF) is a subfield of RL that aims to train agents using human-generated signals. This approach is particularly useful when the reward function is hard to specify or when the environment is too complex for traditional RL methods.",
            52,
        ),
        (
            """## JSON Schema

You can generate a JSON schema from any type of callable: classes, functions, or dataclasses.""",
            24,
        ),
    ],
)
def test_approx_token_count(sentence, expected):
    # Check approx is within 20% of expected
    assert 0.8 <= approx_token_count(sentence) / expected <= 1.2
