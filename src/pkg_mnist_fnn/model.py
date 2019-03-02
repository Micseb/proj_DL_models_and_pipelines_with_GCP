# First try to start Cloud ML uing MNIST example.
import tensorflow as tf
import numpy as np

from .utils import load_data
##########################################################################
#Factor into config:
IMAGE_SHAPE = (28,28)
N_PIXEL = 28 * 28
NUM_LABELS = 10

BATCH_SIZE = 128
EPOCHS = 5
##########################################################################
def parse_images(x):
    return x.reshape(len(x), -1).astype('float32')


def parse_labels(y):
    return y.astype('int32')


def numpy_input_fn(images: np.ndarray,
                   labels: np.ndarray,
                   mode=tf.estimator.ModeKeys.EVAL):
    """
    Return depending on the `mode`-key an Interator which can be use to
    feed into the Estimator-Model. 

    Alternative if a `tf.data.Dataset` named `dataset` would be created:
    `dataset.make_one_shot_iterator().get_next()`
    """
    if mode == tf.estimator.ModeKeys.TRAIN:
        _epochs = EPOCHS
        _shuffle = True
        _num_threads = 2 # This leads to doubling the number of epochs
    else:
        _epochs = 1
        _shuffle = False
        _num_threads = 1

    return tf.estimator.inputs.numpy_input_fn(
        {'x': images},
        y=labels,
        batch_size=BATCH_SIZE,
        num_epochs=_epochs, # Boolean, if True shuffles the queue.
                            # Avoid shuffle at prediction time.
        shuffle=_shuffle,
        queue_capacity=1000, # Integer, number of threads used for reading 
        # and enqueueing. To have predicted order of reading and enqueueing,
        # such as in prediction and evaluation mode, num_threads should be 1.
        num_threads=_num_threads
    )


def serving_input_fn():
    feature_placeholders = {
        'x': tf.placeholder(tf.float32, shape=[None, N_PIXEL])
    }
    features = feature_placeholders
    return tf.estimator.export.ServingInputReceiver(
         features=features, 
         receiver_tensors=feature_placeholders,
         receiver_tensors_alternatives=None
         )


def train_and_evaluate(args):
    """
    Utility function for distributed training on ML-Engine
    www.tensorflow.org/api_docs/python/tf/estimator/train_and_evaluate 
    """
    ##########################################
    # Load Data in Memoery
    # ToDo: replace numpy-arrays
    print('## load data')
    (x_train, y_train), (x_test, y_test) = load_data(
        path=args['data_path'])
    
    x_train = parse_images(x_train)
    x_test = parse_images(x_test)

    y_train = parse_labels(y_train)
    y_test = parse_labels(y_test)

    model = tf.estimator.DNNClassifier(
        hidden_units=[256, 128, 64],
        feature_columns=[tf.feature_column.numeric_column(
            'x', shape=[N_PIXEL, ])],
        model_dir=args['output_dir'],
        n_classes=10,
        optimizer=tf.train.AdamOptimizer,
        # activation_fn=,
        dropout=0.2,
        batch_norm=False,
        loss_reduction='weighted_sum',
        warm_start_from=None,
        config = None
    )
   
    train_spec = tf.estimator.TrainSpec(
        input_fn=numpy_input_fn(
            x_train, y_train, mode=tf.estimator.ModeKeys.TRAIN),
        max_steps=args['train_steps'],
        hooks = None
    )
    exporter = tf.estimator.LatestExporter('exporter', serving_input_fn)
    eval_spec = tf.estimator.EvalSpec(
        input_fn=numpy_input_fn(
            x_test, y_test, mode=tf.estimator.ModeKeys.EVAL),
        steps=None,
        start_delay_secs=args['eval_delay_secs'],
        throttle_secs=args['min_eval_frequency'],
        exporters=exporter
    )
    print("## start training and evaluation")
    tf.estimator.train_and_evaluate(
        estimator=model, train_spec=train_spec, eval_spec=eval_spec)