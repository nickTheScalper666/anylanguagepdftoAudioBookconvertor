from __future__ import annotations
from dataclasses import dataclass
from typing import List
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

@dataclass(frozen=True)
class NllbConfig:
    model_name: str = "facebook/nllb-200-distilled-600M"
    use_mps_if_available: bool = True
    max_new_tokens: int = 512
    num_beams: int = 4

class NllbTranslator:
    def __init__(self, cfg: NllbConfig = NllbConfig()):
        self.cfg = cfg
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(cfg.model_name)

        device = "cpu"
        if cfg.use_mps_if_available and torch.backends.mps.is_available():
            device = "mps"
        self.device = torch.device(device)
        self.model.to(self.device)
        self.model.eval()

    def translate_chunks(self, chunks: List[str], *, src_lang: str, tgt_lang: str) -> List[str]:
        out: List[str] = []
        self.tokenizer.src_lang = src_lang
        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_lang)

        with torch.inference_mode():
            for ch in chunks:
                inputs = self.tokenizer(ch, return_tensors="pt", truncation=True).to(self.device)
                gen = self.model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_new_tokens=self.cfg.max_new_tokens,
                    num_beams=self.cfg.num_beams,
                )
                txt = self.tokenizer.batch_decode(gen, skip_special_tokens=True)[0]
                out.append(txt.strip())
        return out
