# ==================== Logic Parser =========================
# Adapted from the simple logic parser at https://stackoverflow.com/a/2472414 to support logical operands on lists.
import asyncio

from utils.exceptions import InvalidInput, InvalidResponse
from utils.util import log
from wax_chain.wax_market_utils import get_owners


def _and(l1, l2):
    # return [i for i in l1 if i in l2]
    return list(set(l1) & set(l2))


def _or(l1, l2):
    return list(set(l1 + l2))


str_to_tokens = {"and": _and, "or": _or, "(": "(", ")": ")"}


def create_token_lst(s, tokens):
    """
    Turns a raw string and guideline tokens into a set of instruction symbols
    """
    str_to_token = {
        **str_to_tokens,
        **tokens,
    }  # The full set of symbols used in this case
    s = s.replace("(", " ( ")
    s = s.replace(")", " ) ")

    return [str_to_token[it] for it in s.split()]


def find(list_, what, start=0):
    return [i for i, it in enumerate(list_) if it == what and i >= start]


def parentheses(token_list):
    """
    Deals with parentheses.
    :returns: (bool)parentheses_exist, left_paren_pos, right_paren_pos
    """
    left_list = find(token_list, "(")

    if not left_list:
        return False, -1, -1

    left = left_list[-1]

    # can not occur earlier, hence there are args and op.
    right = find(token_list, ")", left + 4)[0]

    return True, left, right


def do_next_token(token_list):
    """
    Does the next appropriate operand in the list of instructions that is token_lst.
    """
    return token_list[1](token_list[0], token_list[2])


def recursive_token_eval(token_list):
    """
    Recursively evaluates the operands in the list of instructions that is token_list.
    """
    """eval a formatted (i.e. of the form 'ToFa(ToF)') string"""
    if not token_list:
        return []

    if len(token_list) == 1:
        return token_list[0]

    has_parens, l_paren, r_paren = parentheses(token_list)

    if not has_parens:
        return do_next_token(token_list)

    token_list[l_paren : r_paren + 1] = [
        do_next_token(token_list[l_paren + 1 : r_paren])
    ]

    return recursive_token_eval(token_list)


def nested_bool_eval(s: str, list_dict: dict) -> list:
    """
    Evaluates the boolean logic expression s, substituting keys in list_dict with their corresponding lists.
    """
    """The actual 'eval' routine,
    if 's' is empty, 'True' is returned,
    otherwise 's' is evaluated according to parentheses nesting.
    The format assumed:
        [1] 'LEFT OPERATOR RIGHT',
        where LEFT and RIGHT are either:
                True or False or '(' [1] ')' (subexpression in parentheses)
    """
    return recursive_token_eval(create_token_lst(s, list_dict))


async def parse_addresses(
    session, text: str = None, blacklist: set = None
) -> (str, str):
    maximum = None
    use_blacklist = True
    # Pre-processing
    if "-" in text:
        ind = text.find("-") - 1
        params = text[ind:].split()
        text = text[0:ind].strip()
        count = 0
        for param in params:
            if param == "-max":
                try:
                    maximum = int(params[count + 1])
                except ValueError:
                    raise InvalidInput(
                        "Invalid maximum. -max must be followed by an integer."
                    )
            elif param == "-noblacklist":
                use_blacklist = False
            count += 1
        log(
            f"Found - in text. maximum = {maximum}, use_blacklist = {use_blacklist}",
            "DBUG",
        )
    t_text = text.replace(")", " ) ")
    t_text = t_text.replace("(", " ( ")
    words = t_text.split()
    ids = []

    for word in words:
        try:
            ids.append(int(word))
        except ValueError:
            if word not in str_to_tokens:
                raise InvalidInput(
                    "Only template ids, brackets, `and`, and `or` are supported."
                )
    # Get the template id owners
    _tasks = []
    for card_id in ids:
        _tasks.append(asyncio.create_task(get_owners(card_id, session)))
    responses = await asyncio.gather(
        *_tasks
    )  # a list of the list of owners of each card specified in the command
    lists_dict = {
        str(template_id): list_ for template_id, list_ in responses
    }  # dict id:list of owners
    log(str(lists_dict), "DBUG")
    # Parse boolean list logic
    try:
        resultant_list = nested_bool_eval(text, lists_dict)
    except AttributeError:
        raise InvalidInput("Incomplete command.")
    except IndexError:
        raise InvalidInput(
            "Make sure you use brackets whenever the result could be ambiguous."
        )

    # Empty address list
    if resultant_list is None or len(resultant_list) < 1:
        raise InvalidResponse("No addresses found with that combination of cards.")
    # Exclude invalid addresses
    resultant_list = [i for i in resultant_list if i is not None and len(i) > 0]
    # Exclude blacklisted addresses
    if use_blacklist:
        resultant_list = [
            i
            for i in resultant_list
            if i is not None and len(i) > 0 and i not in blacklist
        ]
    # Concatenate list if longer than maximum
    if maximum is not None:
        log(f"Using max {maximum}", "DBUG")
        resultant_list = resultant_list[0:maximum]
    return resultant_list
