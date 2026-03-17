from pathlib import Path

import pkg_resources
from symspellpy import SymSpell, Verbosity

_MEDICAL_TERMS_PATH = Path(__file__).parent.parent / "data" / "medical_terms.txt"


class NLPService:
    def __init__(self):
        self._sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self._whitelist: set[str] = set()
        self._loaded = False

    def load(self):
        """Load the SymSpell dictionary and medical whitelist at startup."""
        if self._loaded:
            return
        dict_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_82_765.txt"
        )
        self._sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)

        # Load medical terms whitelist — these words are never flagged as misspellings
        if _MEDICAL_TERMS_PATH.exists():
            self._whitelist = {
                line.strip().lower()
                for line in _MEDICAL_TERMS_PATH.read_text().splitlines()
                if line.strip()
            }

        self._loaded = True

    def add_to_whitelist(self, word: str):
        """Add a custom word to the whitelist at runtime."""
        self._whitelist.add(word.lower())

    def check_text(self, text: str) -> list[dict]:
        """
        Spell-check the given text and return a list of corrections.
        Each correction has: word, correction, offset, length.
        Words in the medical whitelist are skipped.
        """
        corrections = []
        offset = 0

        for token in text.split():
            clean = token.strip(".,!?;:\"'()-")
            if not clean or not clean.isalpha():
                offset = text.find(token, offset) + len(token)
                continue

            # Skip whitelisted medical/domain terms
            if clean.lower() in self._whitelist:
                offset = text.find(token, offset) + len(token)
                continue

            suggestions = self._sym_spell.lookup(
                clean.lower(), Verbosity.CLOSEST, max_edit_distance=2
            )

            if suggestions and suggestions[0].term != clean.lower():
                word_offset = text.find(token, offset)
                best = suggestions[0].term
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
