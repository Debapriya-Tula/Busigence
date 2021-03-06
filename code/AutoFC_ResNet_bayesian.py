# Here bayesian optimization is used for all non string hyperparameters

# Importing the required libraries 
import os
import numpy
import matplotlib.pyplot as plt
import random

from PIL import Image
from keras.preprocessing import image
from keras.applications import ResNet50
from keras import models, layers, callbacks, activations
from keras.backend import tf as ktf
from keras.utils import multi_gpu_model, Sequence
from bayes_opt import BayesianOptimization

from datetime import datetime

import pandas as pd

import GPyOpt, GPy




TRAIN_PATH = os.path.join("Caltech101", "training")
VALID_PATH = os.path.join("Caltech101", "validation")
NUMBER_OF_CLASSES = len(os.listdir(TRAIN_PATH))

# Creating generators from training and validation data
train_datagen = image.ImageDataGenerator()
train_generator = train_datagen.flow_from_directory(TRAIN_PATH, target_size=(224, 224), batch_size=32)

valid_datagen = image.ImageDataGenerator()
valid_generator = valid_datagen.flow_from_directory(VALID_PATH, target_size=(224, 224), batch_size=32)




def get_model(num_layers, num_neurons, dropout, activation, weight_initializer):
    base_model = ResNet50(weights="imagenet")
    for layer in base_model.layers:
        layer.trainable = False

    X = base_model.layers[-2].output
    for _ in range(num_layers):
        X = layers.Dense(num_neurons, activation=activation, kernel_initializer=weight_initializer)(X)
        X = layers.Dropout(dropout)(X)

    X = layers.Dense(NUMBER_OF_CLASSES, activation='softmax')(X)
    model = models.Model(inputs=base_model.inputs, outputs=X)
    return model

try:
    log_df = pd.read_csv('bayes_log.csv', header=0, index_col=['index'])
except FileNotFoundError:
    log_df = pd.DataFrame(columns=['index', 'activation', 'weight_initializer', 'dropout', 'num_neurons', 'num_layers', 'loss'])
    log_df = log_df.set_index('index')

print("Shape:", log_df.shape)

bounds = [
    {'name': 'dropout', 'type': 'continuous', 'domain': (0, 0.99)},
    {'name': 'num_neurons', 'type': 'discrete', 'domain': [2 ** j for j in range(5, 8)]},
    {'name': 'num_layers', 'type': 'discrete', 'domain': range(1, 5)}
    #{'name': 'activation', 'type': 'discrete', 'domain': ['relu', 'tanh', 'sigmoid']},
    #{'name': 'weight_initializer', 'type': 'discrete', 'domain': ['constant', 'normal', 'uniform', 'glorot_uniform', 'glorot_normal', 'he_normal', 'he_uniform', 'orthogonal']}
]

from itertools import product


# Grid search is applied for the string hyper parameters
p_space = {
    'activation': ['relu', 'tanh', 'sigmoid'],
    'weight_initializer': ['constant', 'normal', 'uniform', 'glorot_uniform', 'glorot_normal', 'he_normal', 'he_uniform', 'orthogonal']
}

p_space = list(product(*p_space.values()))

start = datetime.time(datetime.now())
print("Starting:", start)

for combo in p_space:
    print(combo)
    activation, weight_initializer = combo

    temp_df = log_df.loc[log_df['activation'] == activation, :].loc[log_df['weight_initializer'] == weight_initializer, :]
    if temp_df.shape[0] > 0:
        continue

    def model_fit(x):
        model = get_model(
            dropout=float(x[:, 0]),
            num_layers=int(x[:, 2]),
            num_neurons=int(x[:, 1]),
            activation=activation,
            weight_initializer=weight_initializer
        )
        model = multi_gpu_model(model, gpus=2)
        model.compile(optimizer='adagrad', loss='categorical_crossentropy', metrics=['accuracy'])
        model.fit_generator(train_generator, epochs=2, validation_data=valid_generator, verbose=1)
        score = model.evaluate_generator(valid_generator, verbose=1)
        return score[0]


    opt_ = GPyOpt.methods.BayesianOptimization(f=model_fit, domain=bounds)
    opt_.run_optimization(max_iter=5)

    print("""
    Optimized Parameters:
    \t{0}:\t{1}
    \t{2}:\t{3}
    \t{4}:\t{5}
    """.format(bounds[0]["name"],opt_.x_opt[0],
               bounds[1]["name"],opt_.x_opt[1],
               bounds[2]["name"],opt_.x_opt[2]
    ))
    print("optimized loss: {0}".format(opt_.fx_opt))

    log_tuple = (activation, weight_initializer, opt_.x_opt[0], opt_.x_opt[1], opt_.x_opt[2], opt_.fx_opt)
    print("Logging record:", log_tuple)
    log_df.loc[log_df.shape[0], :] = log_tuple
    print("Shape:", log_df.shape)

    log_df.to_csv('AutoFC_ResNet_log_bayesian_Caltech101.csv')

end = datetime.time(datetime.now())
print("Ending:", end)
