"""translate-nllb: translate text between English, Hindi, Marathi and about 200 other languages, on this computer.

Usage: python translate-nllb.py IN.txt OUT.txt [SRC=eng_Latn] [TGT=hin_Deva]   (Marathi: mar_Deva)
One line in, one line out. The model folder is $IDLI_FILES/models/nllb-200-distilled-600M-ct2-int8/.
Licence: CC-BY-NC-4.0, non-commercial use only.
"""
import os
import sys
import time

import ctranslate2
import sentencepiece as spm

src_path, out_path = sys.argv[1], sys.argv[2]
src = sys.argv[3] if len(sys.argv) > 3 else "eng_Latn"
tgt = sys.argv[4] if len(sys.argv) > 4 else "hin_Deva"
d = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "nllb-200-distilled-600M-ct2-int8")

t = time.time()
sp = spm.SentencePieceProcessor(model_file=os.path.join(d, "sentencepiece.bpe.model"))
tr = ctranslate2.Translator(d, device="cpu", compute_type="int8", intra_threads=min(8, os.cpu_count() or 4))
with open(src_path, encoding="utf-8") as f:
    lines = [ln.rstrip("\n") for ln in f]
todo = [i for i, ln in enumerate(lines) if ln.strip()]
batch = [[src] + sp.encode(lines[i], out_type=str) + ["</s>"] for i in todo]
results = tr.translate_batch(batch, target_prefix=[[tgt]] * len(batch), beam_size=4, max_batch_size=16)
out = list(lines)
for i, r in zip(todo, results):
    out[i] = sp.decode(r.hypotheses[0][1:])  # drop the language token
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
print(f"{len(todo)} lines in {time.time() - t:.1f} s")
