import numpy as np 
import tensorflow as tf 
import fasttext as ft 
import math
import sys
from cnn_lstm_crf import CNN_BLSTM_CRF

Word2vec = ft.load_model('vi.bin')

def make_char_dictionary(data_path, dict_path):
	### initialize dictionary set
	char_dictionary = ['<UNK>', '<PAD>']
	### make character dictionary
	f = open(data_path, 'r')
	for row in f:
		row_split = row[:-1].split(' ')
		for word in row:
			for char in word:
				char_dictionary.append(char)
	f.close()
	### remove duplicate characters
	char_dictionary = list(set(char_dictionary))
	### save character dictionary
	f = open(dict_path, 'w')
	for char in char_dictionary:
		f.write(char + '\n')
	f.close()


def load_dictionary(dict_path):
	f = open(dict_path, 'r')
	char_dictionary = set()
	for row in f:
		char_dictionary.add(row[:-1])
	char_dictionary = list(char_dictionary)
	f.close()
	return char_dictionary


def load_char_level_input(f, batch_size, char_dictionary, max_length_word, max_length_sentence):
	# character level presentation in bag of word form: [batch_size, max_length_sentence, max_length_word]
	bow_char_presentation = []
	sen_in_batch = 1
	for row in f:
		# row_presentation: [max_length_sentence, max_length_word]
		row_presentation = []
		row_separated = row[:-1].replace('_', ' ', 1000)
		row_split = row_separated.split(' ')
		for word in row_split:
			# word_presentation: [max_length_word]
			# true characters of a word
			inner_word_presentation = []
			for char in word:
				if (char in char_dictionary):
					inner_word_presentation.append(char_dictionary.index(char))
				else:
					inner_word_presentation.append(char_dictionary.index('<UNK>'))
			# add padding to beginning of presentation
			begin_padding = []
			while (len(begin_padding) < (int((max_length_word - len(inner_word_presentation))/2))):
				begin_padding.append(char_dictionary.index('<PAD>'))
			# add padding to the end of presentation
			end_padding = []
			while ((len(begin_padding) + len(inner_word_presentation) + len(end_padding)) < max_length_word):
				end_padding.append(char_dictionary.index('<PAD>'))
			# combine all 3 parts
			word_presentation = begin_padding + inner_word_presentation + end_padding
		# add true word presentation to row presentation
		row_presentation.append(word_presentation)
		# add padding word presentation to row presentation
		while (len(row_presentation) < max_length_sentence):
			padding_word = []
			for i in range(max_length_word):
				padding_word.append(char_dictionary.index('<PAD>'))
			row_presentation.append(padding_word)
		# add row presentation to output
		bow_char_presentation.append(row_presentation)
		sen_in_batch += 1
		if (sen_in_batch > batch_size):
			break
	return bow_char_presentation

def load_word_level_input(f, batch_size, max_length_sentence):
	seg_data = []
	seg_labels = []
	seg_sequence_length = []
	sen_in_batch = 1
	for row in f:
		row_data = []
		row_labels = []
		row_list = row[:-1].split(' ')
		row_length = 0
		for word in row_list:
			split_word = word.split('_')
			row_length += len(split_word)
			if (len(split_word) == 1):
				row_data.append(Word2vec[split_word[0]])
				row_labels.append(1)
			if (len(split_word) > 1):
				row_data.append(Word2vec[split_word[0]])
				row_labels.append(1)
				for i in range(1, len(split_word) - 1):
					row_data.append(Word2vec[split_word[i]])
					row_labels.append(2)
				row_data.append(Word2vec[split_word[-1]])
				row_labels.append(3)
		while (len(row_data) < max_length_sentence):
			row_data.append(np.zeros(100))
			row_labels.append(0)
		seg_data.append(row_data)
		seg_labels.append(row_labels)
		seg_sequence_length.append(row_length)
		sen_in_batch += 1
		if (sen_in_batch > batch_size):
			break
	return seg_data, seg_labels, seg_sequence_length

def main():
	# parameters
	max_length_word = int(sys.argv[1])			# maximum length of a word	
	max_length_sentence = int(sys.argv[2])		# maximun length of a sentence
	char_embedding_size = int(sys.argv[3])		# size of character embedding
	window_size = int(sys.argv[4])				# size of window in CNN
	number_conv_units = int(sys.argv[5])		# size of character's information of a word
	n_hidden = int(sys.argv[6])					# size of hidden state also cell state in LSTM
	num_tag = int(sys.argv[7])					# number of tags
	batch_size = int(sys.argv[8])				# batch size
	lr = float(sys.argv[9])						# learning rate
	epochs = int(sys.argv[10])					# number of epoch
	percent_GPU = float(sys.argv[11])			# percentage GPU uses
	work = sys.argv[12]							# 'train' or 'test'
	load_data_path = './Vietnamese Word Segmentation/random_corpus/' + sys.argv[13] + '/test_corpus'
	save_model_path = sys.argv[14]
	epoch = int(sys.argv[15])					# evaluate epoch
	# load pretrain model
	# make_char_dictionary('./Vietnamese Word Segmentation/1_file_data/small_train_corpus', './model/cnn_lstm_crf/small_data/char_dictionary')
	char_dictionary = load_dictionary(save_model_path + '/char_dictionary')
	# define our model
	model = CNN_BLSTM_CRF(max_length_word = max_length_word, max_length_sentence = max_length_sentence, char_embedding_size = char_embedding_size, window_size = window_size, number_conv_units = number_conv_units, n_hidden = n_hidden, num_tag = num_tag, char_dictionary = char_dictionary, percent_GPU = percent_GPU, work = work)
	# evaluate model
	model.load_model(save_model_path, epoch)
	f_char = open(load_data_path, 'r')
	f_word = open(load_data_path, 'r')
	start = 0
	cnt = 0
	sum_cnt = 0
	while (start < 61377):
		print('batch: ', start, end = '\r')
		start += 1
		char_input = load_char_level_input(f_char, 1, char_dictionary, max_length_word, max_length_sentence)
		word_input, labels, seqlen = load_word_level_input(f_word, 1, max_length_sentence)
		predict_labels = model.predict(char_input, word_input, seqlen)
		labels = labels[0][:seqlen[0]]
		predict_labels.append(1)
		labels.append(1)
		dd = 0
		for i in range(1, seqlen[0] + 1):
			if (labels[i] == 1):
				sum_cnt += 1
				p_labels = predict_labels[dd:i]
				t_labels = labels[dd:i]
				if (p_labels == t_labels):
					cnt += 1
				dd = i
	print(cnt, ' / ', sum_cnt)
	print(cnt/sum_cnt)
	f_char.close()
	f_word.close()


if __name__ == '__main__':
	main()