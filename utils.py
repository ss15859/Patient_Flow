import os
import datetime

import IPython
import IPython.display
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
tf.random.set_seed(0)



class WindowGenerator():
	def __init__(self, input_width, label_width,
			   train_df, val_df, test_df,
			   label_columns=None):
	# Store the raw data.
		self.train_df = train_df
		self.val_df = val_df
		self.test_df = test_df

		# Work out the label column indices.
		self.label_columns = label_columns
		if label_columns is not None:
		  self.label_columns_indices = {name: i for i, name in
										enumerate(label_columns)}
		self.column_indices = {name: i for i, name in
							   enumerate(train_df.columns)}

		# Work out the window parameters.
		self.input_width = input_width
		self.label_width = label_width
		self.shift = label_width

		self.total_window_size = input_width + self.shift

		self.input_slice = slice(0, input_width)
		self.input_indices = np.arange(self.total_window_size)[self.input_slice]

		self.label_start = self.total_window_size - self.label_width
		self.labels_slice = slice(self.label_start, None)
		self.label_indices = np.arange(self.total_window_size)[self.labels_slice]

	def __repr__(self):
		return '\n'.join([
			f'Total window size: {self.total_window_size}',
			f'Input indices: {self.input_indices}',
			f'Label indices: {self.label_indices}',
			f'Label column name(s): {self.label_columns}'])

	def split_window(self, features):
		inputs = features[:, self.input_slice, :]
		labels = features[:, self.labels_slice, :]
		if self.label_columns is not None:
			labels = tf.stack(
				[labels[:, :, self.column_indices[name]] for name in self.label_columns],
				axis=-1)

		# Slicing doesn't preserve static shape information, so set the shapes
		# manually. This way the `tf.data.Datasets` are easier to inspect.
		inputs.set_shape([None, self.input_width, None])
		labels.set_shape([None, self.label_width, None])

		return inputs, labels



	def plot(self, model=None, plot_col='Number of Patients', max_subplots=4):
		
		inputs, labels = self.example
		plt.figure(figsize=(12, 20))
		plot_col_index = self.column_indices[plot_col]
		max_n = min(max_subplots, len(inputs))
		for n in range(max_n):
			plt.subplot(max_n, 1, n+1)
			plt.ylabel(f'{plot_col}')
			plt.plot(self.input_indices, inputs[n, :, plot_col_index],
					 label='Inputs', marker='.', zorder=-10)

			if self.label_columns:
			  label_col_index = self.label_columns_indices.get(plot_col, None)
			else:
			  label_col_index = plot_col_index

			if label_col_index is None:
			  continue

			plt.scatter(self.label_indices, labels[n, :, label_col_index],
						edgecolors='k', label='Observed', c='#2ca02c', s=64)
			if model is not None:
			  predictions = model(inputs)
			  plt.scatter(self.label_indices, predictions[n, :],
						  marker='X', edgecolors='k', label='Predictions',
						  c='#ff7f0e', s=64)

			if n == 0:
			  plt.legend()

		# plt.xlabel('Time [h]')

	def make_dataset(self, data,shuffle,seq_stride=1):
		data = np.array(data, dtype=np.float32)
		ds = tf.keras.utils.timeseries_dataset_from_array(
		  data=data,
		  targets=None,
		  sequence_length=self.total_window_size,
		  sequence_stride=seq_stride,
		  shuffle=shuffle,
		  batch_size=32,)

		ds = ds.map(self.split_window)

		return ds

	@property
	def train(self):
		return self.make_dataset(self.train_df,shuffle=True)

	@property
	def val(self):
		return self.make_dataset(self.val_df,shuffle=True)

	@property
	def test(self):
		return self.make_dataset(self.test_df,shuffle=False,seq_stride= self.label_width)

	@property
	def example(self):
		"""Get and cache an example batch of `inputs, labels` for plotting."""
		result = getattr(self, '_example', None)
		if result is None:
			# No example batch was found, so get one from the `.train` dataset
			result = next(iter(self.train))
			# And cache it for next time
			self._example = result
		return result





# def compile_and_fit(model, window, patience=200,MAX_EPOCHS=1000):
# 	early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
# 												patience=patience,
# 												mode='min',
# 												restore_best_weights=True)

# 	checkpoint_name = 'best_model_numfeatures='+str(window.example[0].shape[2])+'.ckpt'

# 	checkpoint = tf.keras.callbacks.ModelCheckpoint(checkpoint_name, 
# 					monitor="val_loss", mode="min", 
# 					save_best_only=True, verbose=0)

# 	model.compile(loss=tf.keras.losses.MeanSquaredError(),
# 			optimizer=tf.keras.optimizers.Adam(),
# 			metrics=[tf.keras.metrics.MeanAbsoluteError(),
# 			tf.keras.metrics.MeanAbsolutePercentageError(),
# 			tf.keras.losses.MeanSquaredError()])

# 	history = model.fit(window.train, epochs=MAX_EPOCHS,
# 				  validation_data=window.val,
# 				  callbacks=[early_stopping,checkpoint])

# 	model.load_weights(checkpoint_name)

# 	return history



class lstm(tf.keras.Model):


	def __init__(self,input_width,label_width,input_features=1):

		super().__init__() 
		self.IN_STEPS = input_width
		self.OUT_STEPS = label_width
		self.input_features = input_features


		self.compile(loss=tf.keras.losses.MeanSquaredError(),
			optimizer=tf.keras.optimizers.Adam(),
			metrics=[tf.keras.metrics.MeanAbsoluteError()])

		self.lstm_layer = tf.keras.layers.LSTM(64, return_sequences=False)
		self.dense_layer = tf.keras.layers.Dense(self.OUT_STEPS,
						  kernel_initializer=tf.initializers.zeros())


	def call(self,inputs):

		output_LSTM = self.lstm_layer(inputs)
		outputs = self.dense_layer(output_LSTM)

		return outputs
	
	def fit(self,train_input,val_input):

		early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
											patience=2000,
											mode='min',
											restore_best_weights=True)

		checkpoint_name = 'checkpoints/best_model_numfeatures='+str(self.input_features)+' output_width=' +str(self.OUT_STEPS) +'.ckpt'

		checkpoint = tf.keras.callbacks.ModelCheckpoint(checkpoint_name, 
					monitor="val_loss", mode="min", 
					save_best_only=True, verbose=0)

		history = super(lstm, self).fit(train_input,epochs=2000,
				  validation_data=val_input,
				  callbacks=[early_stopping,checkpoint])

		self.load_weights(checkpoint_name)

		return history







