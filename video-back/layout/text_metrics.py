from __future__ import annotations

import math


class TextMetrics:
    """A lightweight estimator for layout-time text sizing.

    The estimator intentionally avoids browser or font-engine dependencies so it
    can run inside validators and unit tests. It trades precision for speed and
    determinism.
    """

    def estimate_text_width(self, text: str, font_size: int) -> float:
        width = 0.0
        for char in text:
            width += self._char_width(char, font_size)
        return width

    def estimate_lines(self, text: str, font_size: int, width: float) -> int:
        if not text:
            return 1
        if width <= 0:
            return max(1, len(text))

        lines = 1
        current_width = 0.0

        for token in self._tokenize(text):
            token_width = self.estimate_text_width(token, font_size)

            if token == "\n":
                lines += 1
                current_width = 0.0
                continue

            if current_width == 0 and token_width <= width:
                current_width = token_width
                continue

            if current_width + token_width <= width:
                current_width += token_width
                continue

            if token_width <= width:
                lines += 1
                current_width = token_width
                continue

            for char in token:
                char_width = self._char_width(char, font_size)
                if current_width and current_width + char_width > width:
                    lines += 1
                    current_width = 0.0
                current_width += char_width

        return max(1, lines)

    def estimate_height(
        self,
        text: str,
        font_size: int,
        line_height: float,
        width: float,
    ) -> float:
        lines = self.estimate_lines(text, font_size, width)
        return lines * font_size * line_height

    def _tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        current = ""

        for char in text:
            if char == "\n":
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(char)
                continue

            if char.isspace():
                current += char
                tokens.append(current)
                current = ""
                continue

            current += char

        if current:
            tokens.append(current)
        return tokens

    def _char_width(self, char: str, font_size: int) -> float:
        if char == "\n":
            return 0.0
        if char.isspace():
            return font_size * 0.33
        if self._is_cjk(char):
            return float(font_size)
        if char.isdigit():
            return font_size * 0.56
        if char.isalpha():
            if char.isupper():
                return font_size * 0.62
            return font_size * 0.55
        return font_size * 0.5

    def _is_cjk(self, char: str) -> bool:
        code = ord(char)
        return any(
            [
                0x4E00 <= code <= 0x9FFF,
                0x3400 <= code <= 0x4DBF,
                0x3040 <= code <= 0x30FF,
                0xAC00 <= code <= 0xD7AF,
            ]
        )
