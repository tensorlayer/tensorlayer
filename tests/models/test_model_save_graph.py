#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import tensorflow as tf
import tensorlayer as tl
from tensorlayer.layers import *
from tensorlayer.models import *

from tests.utils import CustomTestCase


def basic_static_model():
    ni = Input((None, 24, 24, 3))
    nn = Conv2d(16, (5, 5), (1, 1), padding='SAME', act=tf.nn.relu, name="conv1")(ni)
    nn = MaxPool2d((3, 3), (2, 2), padding='SAME', name='pool1')(nn)

    nn = Conv2d(16, (5, 5), (1, 1), padding='SAME', act=tf.nn.relu, name="conv2")(nn)
    nn = MaxPool2d((3, 3), (2, 2), padding='SAME', name='pool2')(nn)

    nn = Flatten(name='flatten')(nn)
    nn = Dense(100, act=None, name="dense1")(nn)
    M = Model(inputs=ni, outputs=nn)
    return M


class Model_Save_and_Load_without_weights(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing save_graph, load_graph, without weights #####")

    def test_save(self):
        M1 = basic_static_model()
        print("Model config = \n", M1.config)
        print("Model = \n", M1)
        M1.save(filepath="basic_model_without_weights.hdf5", save_weights=False)
        M2 = Model.load(filepath="basic_model_without_weights.hdf5", load_weights=False)

        self.assertEqual(M1.config, M2.config)


def get_model(inputs_shape):
    ni = Input(inputs_shape)
    nn = Dropout(keep=0.8)(ni)
    nn = Dense(n_units=800, act=tf.nn.relu, in_channels=784)(nn) # in_channels is optional in this case as it can be inferred by the previous layer
    nn = Dropout(keep=0.8)(nn)
    nn = Dense(n_units=800, act=tf.nn.relu, in_channels=800)(nn) # in_channels is optional in this case as it can be inferred by the previous layer
    nn = Dropout(keep=0.8)(nn)
    nn = Dense(n_units=10, act=tf.nn.relu, in_channels=800)(nn) # in_channels is optional in this case as it can be inferred by the previous layer
    M = Model(inputs=ni, outputs=nn)
    return M


class Model_Save_with_weights(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing save_graph, after training, with weights #####")

    def test_save(self):
        tl.logging.set_verbosity(tl.logging.DEBUG)
        X_train, y_train, X_val, y_val, X_test, y_test = tl.files.load_mnist_dataset(shape=(-1, 784))
        MLP = get_model([None, 784])
        print(MLP)
        n_epoch = 3
        batch_size = 500
        train_weights = MLP.weights
        optimizer = tf.optimizers.Adam(lr=0.0001)

        for epoch in range(n_epoch):  ## iterate the dataset n_epoch times
            print("epoch = ", epoch)

            for X_batch, y_batch in tl.iterate.minibatches(X_train, y_train, batch_size, shuffle=True):
                MLP.train()  # enable dropout

                with tf.GradientTape() as tape:
                    ## compute outputs
                    _logits = MLP(X_batch)  # alternatively, you can use MLP(x, is_train=True) and remove MLP.train()
                    ## compute loss and update model
                    _loss = tl.cost.cross_entropy(_logits, y_batch, name='train_loss')

                grad = tape.gradient(_loss, train_weights)
                optimizer.apply_gradients(zip(grad, train_weights))

        MLP.eval()

        val_loss, val_acc, n_iter = 0, 0, 0
        for X_batch, y_batch in tl.iterate.minibatches(X_val, y_val, batch_size, shuffle=False):
            _logits = MLP(X_batch)  # is_train=False, disable dropout
            val_loss += tl.cost.cross_entropy(_logits, y_batch, name='eval_loss')
            val_acc += np.mean(np.equal(np.argmax(_logits, 1), y_batch))
            n_iter += 1
        print("   val loss: {}".format(val_loss / n_iter))
        print("   val acc:  {}".format(val_acc / n_iter))

        MLP.save("MLP.hdf5")


class Model_Load_with_weights_and_train(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing load_graph, after training, with weights, and train again #####")

    def test_save(self):
        MLP = Model.load("MLP.hdf5",)

        MLP.eval()

        n_epoch = 3
        batch_size = 500
        train_weights = MLP.weights
        optimizer = tf.optimizers.Adam(lr=0.0001)
        X_train, y_train, X_val, y_val, X_test, y_test = tl.files.load_mnist_dataset(shape=(-1, 784))
        val_loss, val_acc, n_iter = 0, 0, 0
        for X_batch, y_batch in tl.iterate.minibatches(X_val, y_val, batch_size, shuffle=False):
            _logits = MLP(X_batch)  # is_train=False, disable dropout
            val_loss += tl.cost.cross_entropy(_logits, y_batch, name='eval_loss')
            val_acc += np.mean(np.equal(np.argmax(_logits, 1), y_batch))
            n_iter += 1
        print("   val loss: {}".format(val_loss / n_iter))
        print("   val acc:  {}".format(val_acc / n_iter))
        assert val_acc > 0.7

        for epoch in range(n_epoch):  ## iterate the dataset n_epoch times
            print("epoch = ", epoch)

            for X_batch, y_batch in tl.iterate.minibatches(X_train, y_train, batch_size, shuffle=True):
                MLP.train()  # enable dropout

                with tf.GradientTape() as tape:
                    ## compute outputs
                    _logits = MLP(X_batch)  # alternatively, you can use MLP(x, is_train=True) and remove MLP.train()
                    ## compute loss and update model
                    _loss = tl.cost.cross_entropy(_logits, y_batch, name='train_loss')

                grad = tape.gradient(_loss, train_weights)
                optimizer.apply_gradients(zip(grad, train_weights))

        MLP.save("MLP.hdf5")


def create_base_network(input_shape):
    '''Base network to be shared (eq. to feature extraction).
    '''
    input = Input(shape=input_shape)
    x = Flatten()(input)
    x = Dense(128, act=tf.nn.relu)(x)
    x = Dropout(0.9)(x)
    x = Dense(128, act=tf.nn.relu)(x)
    x = Dropout(0.9)(x)
    x = Dense(128, act=tf.nn.relu)(x)
    return Model(input, x)


def get_siamese_network(input_shape):
    """Create siamese network with shared base network as layer
    """
    base_layer = create_base_network(input_shape).as_layer()

    ni_1 = Input(input_shape)
    ni_2 = Input(input_shape)
    nn_1 = base_layer(ni_1)
    nn_2 = base_layer(ni_2)
    return Model(inputs=[ni_1, ni_2], outputs=[nn_1, nn_2])


class Reuse_ModelLayer_test(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing save_graph, load_graph, including ModelLayer and reuse  #####")

    def test_save(self):
        input_shape = (None, 784)
        M1 = get_siamese_network(input_shape)
        print("Model config = \n", M1.config)
        print("Model = \n", M1)
        M1.save(filepath="siamese.hdf5", save_weights=False)
        M2 = Model.load(filepath="siamese.hdf5", load_weights=False)

        self.assertEqual(M1.config, M2.config)


class Vgg_LayerList_test(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing save_graph, load_graph, including LayerList  #####")

    def test_save(self):
        M1 = tl.models.vgg16(mode='static')
        print("Model config = \n", M1.config)
        print("Model = \n", M1)
        M1.save(filepath="vgg.hdf5", save_weights=False)
        M2 = Model.load(filepath="vgg.hdf5", load_weights=False)

        self.assertEqual(M1.config, M2.config)


class List_inputs_outputs_test(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing model with list inputs and outputs  #####")

    def test_list_inputs_outputs(self):
        ni_1 = Input(shape=[4, 16])
        ni_2 = Input(shape=[4, 32])
        a_1 = Dense(80)(ni_1)
        b_1 = Dense(160)(ni_2)
        concat = Concat()([a_1, b_1])
        a_2 = Dense(10)(concat)
        b_2 = Dense(20)(concat)

        M1 = Model(inputs=[ni_1, ni_2], outputs=[a_2, b_2])
        print("Model config = \n", M1.config)
        print("Model = \n", M1)
        M1.save(filepath="list.hdf5", save_weights=False)
        M2 = Model.load(filepath="list.hdf5", load_weights=False)

        self.assertEqual(M1.config, M2.config)


class basic_dynamic_model(Model):
    def __init__(self):
        super(basic_dynamic_model, self).__init__()
        self.conv1 = Conv2d(16, (5, 5), (1, 1), padding='SAME', act=tf.nn.relu, in_channels=3, name="conv1")
        self.pool1 = MaxPool2d((3, 3), (2, 2), padding='SAME', name='pool1')

        self.conv2 = Conv2d(16, (5, 5), (1, 1), padding='SAME', act=tf.nn.relu, in_channels=16, name="conv2")
        self.pool2 = MaxPool2d((3, 3), (2, 2), padding='SAME', name='pool2')

        self.flatten = Flatten(name='flatten')
        self.dense1 = Dense(100, act=None, in_channels=576, name="dense1")
        self.dense2 = Dense(10, act=None, in_channels=100, name="dense2")

    def forward(self, x):
        x = self.conv1(x)
        x = self.pool1(x)
        x = self.conv2(x)
        x = self.pool2(x)
        x = self.flatten(x)
        x = self.dense1(x)
        x = self.dense2(x)
        return x


class Exception_test(CustomTestCase):

    @classmethod
    def setUpClass(cls):
        print("##### begin testing exception in dynamic mode  #####")

    def test_exception(self):
        M1 = basic_dynamic_model()
        try:
            M1.save("dynamic.hdf5", save_weights=False)
        except Exception as e:
            self.assertIsInstance(e, RuntimeError)
            print(e)

        try:
            print(M1.config)
        except Exception as e:
            self.assertIsInstance(e, RuntimeError)
            print(e)

        M2 = basic_static_model()
        M2.save("basic_static_mode.hdf5", save_weights=False)
        try:
            M3 = Model.load("basic_static_mode.hdf5")
        except Exception as e:
            self.assertIsInstance(e, RuntimeError)
            print(e)


if __name__ == '__main__':

    tl.logging.set_verbosity(tl.logging.DEBUG)

    unittest.main()
