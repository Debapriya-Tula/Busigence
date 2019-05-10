import os
import numpy
import matplotlib.pyplot as plt
import random

from PIL import Image
from keras.preprocessing import image
from keras.applications import ResNet50
from keras import models, layers, callbacks, activations
from keras.backend import tf as ktf

train_images = []
train_images_labels = []
TRAIN_PATH = os.path.join("Caltech101", "training")
VALID_PATH = os.path.join("Caltech101", "validation")
NUMBER_OF_CLASSES = len(os.listdir(TRAIN_PATH))

# Creating generators from training and validation data
train_datagen = image.ImageDataGenerator()
train_generator = train_datagen.flow_from_directory(TRAIN_PATH, target_size=(224, 224), batch_size=32)

valid_datagen = image.ImageDataGenerator()
valid_generator = valid_datagen.flow_from_directory(VALID_PATH, target_size=(224, 224), batch_size=32)

# Freezing the ResNet50 layers
base_model = ResNet50(weights="imagenet")
for layer in base_model.layers:
	layer.trainable = False

X = base_model.layers[-2].output


for activation in ["relu", "leaky", "tanh", "sigmoid"]:
	for neurons in (2 ** j for j in range(6, 13)):
		print("Model:", activation, neurons)
		X = layers.Dense(128, activation="relu")(X)
		X = layers.Dense(NUMBER_OF_CLASSES, activation="softmax")(X)

		new_model = models.Model(inputs=base_model.input, outputs=X)
		new_model.compile(optimizer='adagrad', loss='categorical_crossentropy', metrics=["accuracy"])
		new_model.fit_generator(train_generator, validation_data=valid_generator, epochs=10, callbacks=[early_callback])
		FILE_NAME = f"{activation}{neurons}.h5"
		FILE_PATH = os.path.join("AutoFC_ResNet", "saved_models", FILE_NAME)
		print(f"Saving model {FILE_NAME}.")
		new_model.save(FILE_PATH)

		print(new_model.evaluate_generator(valid_generator, verbose=1))
		print(new_model.metrics_names)


param_grid = {
	'activation': ['relu', 'tanh', 'sigmoid'],
	'neurons': (2  ** j for j in range(6, 13)),
	'dropout': numpy.arange(0, 0.99, 0.1),
	'weight_initializer': ['constant', 'normal', 'uniform', 'glorot_uniform', 'glorot_normal', 'he_normal', 'he_uniform', 'orthogonal'],
	'num_layers': range(1, 5)
}


from itertools import combinations,product
import time
import random

	
num_layers = param_grid['num_layers']
inner_grid = {key: param_grid[key] for key in param_grid.keys() if key != 'num_layers'}
print("inner grid is:",inner_grid)
inner_hyper = product(*inner_grid.values())

for i in num_layers:
	we_need = list(product(*[inner_hyper for _ in range(i)]))
	
	for j in we_need:
		act_list = []
		neu_list = []
		drop_list = []
		weight_list = []

		for k in j:
			activation = k[0]
			neurons = k[1]
			dropout = k[2]
			weight_init = k[3]

			act_list.append(activation)
			neu_list.append(neurons)
			drop_list.append(dropout)
			weight_list.append(weight_init)
			

			
			print("Model:", i, activation, neurons, dropout, weight_init)
			X = layers.Dense(neurons, activation=activation, kernel_initializer=weight_init)(X)
			X = layers.Dropout(dropout)(X)
		X = layers.Dense(NUMBER_OF_CLASSES, activation="softmax")(X)
	
		new_model = models.Model(inputs=base_model.input, outputs=X)
		new_model.compile(optimizer='adagrad', loss='categorical_crossentropy', metrics=["accuracy"])
		start = time.time()
		history = new_model.fit_generator(train_generator, validation_data=valid_generator, epochs=2, callbacks=[early_callback])

		time_taken = time.time() - start
		print(new_model.evaluate_generator(valid_generator, verbose=1))
		print(new_model.metrics_names)


		print("Time:", time_taken)

	# log the reults in the log dataframe
		loss, acc = new_model.evaluate_generator(train_generator)
		val_loss, val_acc = new_model.evaluate_generator(valid_generator)
		log_tuple = (i, act_list, neu_list, drop_list, weight_list, time_taken, loss, acc, val_loss, val_acc)
		print("Logging results:", log_tuple)
		log_df.loc[log_df.shape[0]] = log_tuple
		print(log_df.shape)

		if log_df.shape[0] <= 5:
			print(log_df.head())

#print(log_df.head())
log_df.to_csv(os.path.join("AutoFC_ResNet", "AutoFC_ResNet_log_gridsearch_Caltech101.csv"))