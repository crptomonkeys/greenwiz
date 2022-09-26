import operator
import random
from math import floor
from typing import Union

cards = [
    "monkeyprinter go brrr",
    "the all-nighter",
    "to the moon",
    "defi yield farmer",
    "this is fine",
    "monkey the frog",
    "unimonkey",
    "monkeydrop",
    "supermonkey",
    "banana republic",
    "the great pampkin",
    "nifty witch",
    "frankenstein's monkey",
    "monkey brrrains",
    "monkey krueger",
    "mummkey",
    "the yellow ritual",
    "never-ending halloween",
    "fudbusters",
    "monkey king",
    "sailor moonkey",
    "the monkeylorian",
    "hodlor!",
    "monkey mcduck",
    "chreeestmas monkey",
    "monkey claus",
    "the market maker",
    "the bounty hunter",
    "new year's monkey (2021)",
    "the blue wizard",
    "the pro-waxxer",
    "the anti-waxxer",
    "planet of the monkeys",
    "the expanse",
    "serenifty",
    "miner monkey",
    "monkey miner",
    "staking queen",
    "bull monkey",
    "the green wizard",
    "bear monkey",
    "hitchhiker monkey",
    "nyan monkey",
    "llama monkey",
    "o'patrick the monkey",
    "3rd banniversary",
    "cluckey",
    "the nifty shopper",
    "planet banance",
    "the yellow wizard",
    "wrapped monkey",
    "the designer",
    "uncommon pizza",
    "moonkie",
    "doge days",
    "the shill",
    "buy the dip",
    "bought the dip",
    "store of value",
    "the red wizard",
    "monkey disco",
    "pool party",
    "junk art monkey",
    "one year later",
    "banano whale",
    "neomonkey",
    "tricked monkey",
    "count bancula",
    "spookey",
    "the purple wizard",
    "the urban jungle",
    "dyor monkey",
    "abominable monkey",
    "froskey",
    "gingerbread monkey",
    "new year's monkey (2022)",
    "monkeytv",
    "monkey-chan",
    "banano sunday",
    "the white wizard",
    "cupid monkey",
]

ops = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}

card_dict = {i + 1: j for i, j in enumerate(cards)}


def m_n(m: str) -> int:
    """Converts a card to its number representation."""
    return cards.index(m.lower()) + 1


def n_m(n: int) -> str:
    """Converts a number to its corresponding card."""
    return cards[max(n - 1, 0)].upper()


def n_m_op(n: Union[int, str]) -> str:
    """Converts n to its corresponding card if it is a string, otherwise leaves it as is."""
    if type(n) is int:
        return n_m(n)
    return n


def _rand(_min=1, _max=10000) -> int:
    """Returns a random card index."""
    return random.randint(_min, min(len(cards) + 1, _max))


def randomcalc(difficulty: int = 1) -> tuple[list, int]:
    """Creates a random math question."""
    if difficulty != 1:
        raise NotImplementedError
    num1, num2 = 0, 0
    if difficulty == 1:
        op = random.choice(list(ops.keys()))
        if op == "-":
            num1 = num2 = _rand(_min=10)
            while num2 == num1:
                num2 = _rand(_max=num1)
        elif op == "+":
            num1 = _rand(_max=len(cards) - 10)
            num2 = _rand(_max=len(cards) - num1)
        elif op in "*/":
            num1 = _rand(_max=floor(len(cards) / 2))
            num2 = _rand(_max=floor(len(cards) / num1))
        if op == "/":
            num1, answer = num1 * num2, num1
        else:
            answer = ops.get(op)(num1, num2)

        return [num1, op, num2], answer
    # formula = []
    # for i in range(1, difficulty+1):
    #     mult_step = random.choice([True, False])
    #     if mult_step:
    # TODO multi-operator quiz questions for higher difficulties


def rand_monkeymath(difficulty: int = 1):
    """Generate a random math question and return the monkeymath-ified question and answer"""
    question_bits, ans = randomcalc(difficulty)
    answer = n_m(ans)
    question = "What is " + " ".join(n_m_op(bit) for bit in question_bits) + "?"
    return question, answer
