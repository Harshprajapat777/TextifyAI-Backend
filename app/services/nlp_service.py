import pkg_resources
from symspellpy import SymSpell, Verbosity


class NLPService:
    def __init__(self):
        self._sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self._loaded = False

    def load(self):
        """Load the SymSpell dictionary at startup."""
        if self._loaded:
            return
        dict_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_82_765.txt"
        )
        self._sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
        self._loaded = True

    def check_text(self, text: str) -> list[dict]:
        """
        Spell-check the given text and return a list of corrections.
        Each correction has: word, suggestions, offset.
        """
        corrections = []
        offset = 0

        for token in text.split():
            # Strip punctuation for lookup but keep original for offset
            clean = token.strip(".,!?;:\"'()-")
            if not clean or not clean.isalpha():
                offset = text.find(token, offset) + len(token)
                continue

            suggestions = self._sym_spell.lookup(
                clean.lower(), Verbosity.CLOSEST, max_edit_distance=2
            )

            # If the top suggestion differs from the original word, it's a misspelling
            if suggestions and suggestions[0].term != clean.lower():
                word_offset = text.find(token, offset)
                best = suggestions[0].term
                # Match original casing
                if clean[0].isupper():
                    best = best.capitalize()
                corrections.append(
                    {
                        "word": clean,
                        "correction": best,
                        "offset": word_offset,
                        "length": len(clean),
                    }
                )

            offset = text.find(token, offset) + len(token)

        return corrections


nlp_service = NLPService()
