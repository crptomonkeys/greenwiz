vowels = ["a", "i", "e", "o", "u", "y", "A", "E", "I", "O", "U", "y"]


def is_vowel(char) -> int:
    return 1 if x in vowels else 0


def total_syllables(text) -> float:
    return sum(list(map(is_vowel, text)))


# Returns the readability of a passage of text as a number using Flesch Readability Ease, higher is simpler
def fleschReadability(text) -> float:
    if len(text) <= 0:
        return 100
    num_words = len(text.split())
    num_sentences = len(text.split("."))
    sentence_length = float(num_words) / num_sentences
    syllables_per_word = total_syllables(text) / num_words
    return 206.835 - 1.015 * sentence_length - 84.6 * syllables_per_word
