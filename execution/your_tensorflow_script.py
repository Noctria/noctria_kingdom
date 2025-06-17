import tensorflow as tf

print("TensorFlow バージョン:", tf.__version__)
print("GPU 利用可能:", tf.config.list_physical_devices('GPU'))
