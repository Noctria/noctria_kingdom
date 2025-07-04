import tensorflow as tf

def test_floor_mod_gpu():
    """✅ FloorMod の演算を GPU で実行し、CUDA の問題を特定"""
    with tf.device('/GPU:0'):
        seed = tf.constant([123456789, 0], dtype=tf.int64)
        casted_seed = tf.cast(tf.math.floormod(seed, tf.int32.max - 1), dtype="int32")
        print("GPU FloorMod result:", casted_seed)

if __name__ == "__main__":
    test_floor_mod_gpu()
