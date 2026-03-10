from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Lang = Literal["en", "ta"]

class LangContext(BaseModel):
    lang: Lang
    output_instruction: str
    ui_label_prefix: str

    @classmethod
    def from_lang(cls, lang: Lang) -> LangContext:
        if lang == "ta":
            return cls(
                lang="ta",
                output_instruction=(
                    "Respond ENTIRELY in Tamil (தமிழ்). "
                    "All field values, explanations, and summaries must be in Tamil. "
                    "Do not mix English and Tamil."
                ),
                ui_label_prefix="ta",
            )
        return cls(
            lang="en",
            output_instruction="Respond in clear, simple English.",
            ui_label_prefix="en",
        )
