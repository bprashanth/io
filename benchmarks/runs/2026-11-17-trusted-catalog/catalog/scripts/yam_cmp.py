import sys, wave, numpy as np
mode, model, wav, out = sys.argv[1:5]
w = wave.open(wav); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
wins = [x[i:i + 15600] for i in range(0, len(x) - 15600, 8000)]
res = []
if mode == "tflite":
    import tensorflow as tf
    it = tf.lite.Interpreter(model_path=model); it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    print(i["shape"], i["dtype"], o["shape"])
    for wv in wins:
        it.set_tensor(i["index"], wv.reshape(i["shape"]).astype(np.float32)); it.invoke(); res.append(it.get_tensor(o["index"]).ravel())
else:
    import onnxruntime as ort
    s = ort.InferenceSession(model, providers=["CPUExecutionProvider"]); inp = s.get_inputs()[0]
    print(inp.shape, s.get_outputs()[0].shape)
    for wv in wins:
        res.append(s.run(None, {inp.name: wv.reshape([d if isinstance(d, int) else 1 for d in inp.shape] if len(inp.shape) > 1 else [-1]).astype(np.float32)})[0].ravel())
np.save(out, np.array(res))
