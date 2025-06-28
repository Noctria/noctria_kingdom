import tensorflow as tf

def test_floor_mod_cpu():
    """✅ FloorMod の演算を CPU で実行し、GPU の問題を特定"""
    with tf.device('/CPU:0'):
        seed = tf.constant([123456789, 0], dtype=tf.int64)
        casted_seed = tf.cast(tf.math.floormod(seed, tf.int32.max - 1), dtype="int32")
        print("CPU FloorMod result:", casted_seed)

if __name__ == "__main__":
    test_floor_mod_cpu()
