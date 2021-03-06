import sys

sys.path.append('../model')

import nltk, sys, os
from conll_table import CONLLTable
from nltk import word_tokenize
from nltk.util import ngrams
from collections import Counter


class CRFDataGenerator:
    def __init__(self, conll_filename, testing=False, label=True):
        self.testing = testing
        self.list_unigrams = []
        self.list_bigrams = []
        self.list_trigrams = []
        self.list_pos_tag_trigrams = []
        self.list_word2vec_unigram = map(str, range(1, 5001))
        self.list_word2vec_bigram = []
        self.label = label
        file_path = os.path.dirname(os.path.abspath(__file__))
        project_path = os.path.abspath(os.path.join(file_path, os.path.pardir))

        self.word2vec_cluster_5000 = self.init_word_embedding_cluster(
            os.path.join(project_path, "../data/word_embedding/word2vec_cluster_5000.txt"))
        self.word2vec_cluster_100 = self.init_word_embedding_cluster(
            os.path.join(project_path, "../data/word_embedding/word2vec_cluster_100.txt"))
        self.CONLL_table = CONLLTable(conll_filename, label)
        # self.CONLL_table = CONLLTable("../../data/output1_test1.conll")
        self.stopword = self.init_stopword_list(file_path, project_path)
        self.aspect_dict = []
        if (testing):
            with open(os.path.join(project_path, "../data/crf/aspect_dict.txt"), "r") as f:
                for line in f:
                    line = line.rstrip()
                    self.aspect_dict.append(line)

            self.list_unigrams = self.init_n_grams(os.path.join(project_path, "../data/crf/list_unigrams.txt"))

    def init_word_embedding_cluster(self, filename):
        cluster = {}
        with open(filename, "r") as f:
            for line in f:
                line = line.rstrip()
                tokens = line.split()
                cluster[tokens[0]] = int(tokens[1])
        return cluster

    def init_n_grams(self, filename):
        result = []
        with open(filename, "r") as f:
            for line in f:
                result.append(line.rstrip())
        return result

    def init_stopword_list(self, file_path, project_path):
        stopword = []
        stopword_filename =  os.path.join(project_path, "preprocess/resource/stopword.txt")
        with open(stopword_filename, "r") as f:
            for line in f:
                stopword.append(line.rstrip())
        return stopword

    def get_list_unigrams(self):
        return self.list_unigrams

    def get_aspect_dictionary(self):
        return self.aspect_dict

    def get_window_text(self, n, tokens, pos):
        center = int(n / 2) + 1
        text = ""
        if (pos < center) and (pos + int(n / 2) >= len(tokens)):
            for i in range(0, len(tokens)):
                text += tokens[i] + " "
        elif (pos < center):
            for i in range(0, pos + int(n / 2) + 1):
                text += tokens[i] + " "
        elif (pos + int(n / 2) >= len(tokens)):
            for i in range(pos - int(n / 2), len(tokens)):
                text += tokens[i] + " "
        else:
            for i in range(pos - int(n / 2), pos + int(n / 2) + 1):
                text += tokens[i] + " "

        return text[:-1]

    def get_n_grams(self, n, sentences):
        result = {}
        for sentence in sentences:
            ngram = Counter(ngrams(sentence.split(), n))
            for key in ngram:
                if key not in result:
                    if (n == 1):
                        result[key[0]] = ngram[key]
                    else:
                        result[key] = ngram[key]
                else:
                    if (n == 1):
                        result[key[0]] += ngram[key]
                    else:
                        result[key] += ngram[key]
        return result

    def get_aspect(self, id_sentence, id_word, word, label):
        aspect = ""
        if (label == "ASPECT-B" or label == "ASPECT-I"):
            aspect = word
            if (label == "ASPECT-I"):
                aspect = word
                prev_id_word = id_word - 1

                while prev_id_word > 0 and self.CONLL_table.is_id_exist(id_sentence, prev_id_word):
                    prev_row = self.CONLL_table.get_row(id_sentence, prev_id_word)
                    temp = aspect
                    aspect = self.CONLL_table.get_word(prev_row) + " " + temp

                    if (self.CONLL_table.get_label(prev_row) != "ASPECT-I"):
                        break;
                    else:
                        prev_id_word -= 1

            next_id_word = id_word + 1
            while next_id_word <= self.CONLL_table.get_sentence_size(id_sentence) + 1 and self.CONLL_table.is_id_exist(
                    id_sentence, next_id_word):
                next_row = self.CONLL_table.get_row(id_sentence, next_id_word)
                if (self.CONLL_table.get_label(next_row) != "ASPECT-I"):
                    break;
                else:
                    aspect += " " + self.CONLL_table.get_word(next_row)
                    next_id_word += 1

        return aspect

    def get_n_grams_feature(self, n, window_text, list_n_grams):
        line = ""
        window_ngrams = Counter(ngrams(nltk.word_tokenize(window_text), n))
        for n_grams in list_n_grams:
            if (n == 1):
                n_grams = (n_grams,)
            if (n_grams in window_ngrams):
                line += " " + str(window_ngrams[n_grams])
            else:
                line += " 0"
        return line

    def get_dependency_tags_feature(self, id_sentence):
        bag_of_vbot = self.init_dependency_tags()
        line = ""
        filter = ["VERB"]
        words = self.CONLL_table.filter_words_by_pos_tag(id_sentence, filter)
        for key1 in words:
            children = self.CONLL_table.get_children(key1, id_sentence)
            for key2, value2 in children.iteritems():
                bag_of_vbot[self.CONLL_table.get_tree_tag(value2)] += 1

            siblings = self.CONLL_table.get_siblings(key1, id_sentence)
            for key2, value2 in siblings.iteritems():
                bag_of_vbot[self.CONLL_table.get_tree_tag(value2)] += 1

        for key, value in bag_of_vbot.iteritems():
            line += " " + str(value)

        return line

    def get_dict_feature(self, label):
        line = ""
        if (label == "ASPECT-B" or label == "ASPECT-I"):
            line += " yes"
        else:
            line += " no"
        return line

    def get_feature(self, id_sentence, id_word):
        row = self.CONLL_table.get_row(id_sentence, id_word)
        label = "O"
        if self.label:
            label = self.CONLL_table.get_label(row)

        word = self.CONLL_table.get_word(row)

        line = self.CONLL_table.get_word(row) + " " + self.CONLL_table.get_pos_tag(row)
        # aspect = self.get_aspect(id_sentence, id_word, word, label)

        # if (self.testing):
        #     if (aspect != ""):
        #         if (aspect in self.aspect_dict):
        #             line += " yes"
        #         else:
        #             line += " no"
        #     else:
        #         line += " no"
        # else:
        #     line += self.get_dict_feature(label)
        #     if (aspect != ""):
        #         if (aspect not in self.aspect_dict):
        #             self.aspect_dict.append(aspect)

        line += " " + self.CONLL_table.get_head_word_of_word(id_sentence, id_word)
        if (word in self.word2vec_cluster_100):
            line += " " + str(self.word2vec_cluster_100[word])
        else:
            line += " -1"

        if (word in self.word2vec_cluster_5000):
            line += " " + str(self.word2vec_cluster_5000[word])
        else:
            line += " -1"

        # window_text = self.get_window_text(5, self.CONLL_table.get_sentence(id_sentence).split(), id_word)
        # line += self.get_n_grams_feature(1, window_text, self.list_unigrams)

        return line + " " + label + "\n"

    def generate_data(self, filename, start1=0, end1=None, start2=None, end2=None):
        if (end1 == None):
            end1 = self.CONLL_table.get_sentences_size()
        else:
            end1 += 1

        reviews = self.CONLL_table.get_sentences(start1, end1)

        if (start2 != None and end2 != None):
            end2 += 1
            reviews += self.CONLL_table.get_sentences(start2, end2)

        filter = ["NOUN", "ADJ", "ADV", "VERB"]
        unigrams = self.get_n_grams(1, self.CONLL_table.get_filtered_sentences(filter, start1, end1, start2, end2))

        if (not self.testing):
            for key in unigrams:
                self.list_unigrams.append(key)

        with open(filename, 'w') as f:
            for i in range(start1, end1):
                for j in range(self.CONLL_table.get_sentence_size(i)):
                    # if (self.CONLL_table.get_pos_tag(self.CONLL_table.get_row(i, j+1)) != "PUNCT"):
                    # if (self.CONLL_table.get_word(self.CONLL_table.get_row(i, j+1)) not in self.stopword):
                    # 	f.write(self.get_feature(i, j+1))
                    f.write(self.get_feature(i, j + 1))
                f.write("\n")

            if (start2 != None and end2 != None):
                for i in range(start2, end2):
                    for j in range(self.CONLL_table.get_sentence_size(i)):
                        # if (self.CONLL_table.get_pos_tag(self.CONLL_table.get_row(i, j+1)) != "PUNCT"):
                        # if (self.CONLL_table.get_word(self.CONLL_table.get_row(i, j+1)) not in self.stopword):
                        # 	f.write(self.get_feature(i, j+1))
                        f.write(self.get_feature(i, j + 1))
                    f.write("\n")


if __name__ == '__main__':
    if (len(sys.argv) == 4):
        filename = sys.argv[1]
        conll_filename = sys.argv[2]
        if (sys.argv[3].lower() == "true"):
            label = True
        else:
            label = False
        testing = False
        start1 = 0
        end1 = None
        start2 = None
        end2 = None
    elif (len(sys.argv) == 7):
        filename = sys.argv[1]
        conll_filename = sys.argv[2]
        if (sys.argv[3].lower() == "true"):
            label = True
        else:
            label = False
        if (sys.argv[4].lower() == "true"):
            testing = True
        else:
            testing = False
        start1 = int(sys.argv[5])
        end1 = int(sys.argv[6])
        start2 = None
        end2 = None
    elif (len(sys.argv) == 9):
        filename = sys.argv[1]
        conll_filename = sys.argv[2]
        if (sys.argv[3].lower() == "true"):
            label = True
        else:
            label = False
        if (sys.argv[4].lower() == "true"):
            testing = True
        else:
            testing = False
        start1 = int(sys.argv[5])
        end1 = int(sys.argv[6])
        start2 = int(sys.argv[7])
        end2 = int(sys.argv[8])
    else:
        print("Syntax: ", sys.argv[0], "<output file> <conll file> <label> <testing> <start1> <end1> <start2> <end2>")
        sys.exit(1)

    cdg = CRFDataGenerator(conll_filename, testing, label)
    cdg.generate_data(filename, start1, end1, start2, end2)

    # if (not testing):
    #     with open("../../data/crf/aspect_dict.txt", "w") as f:
    #         for word in cdg.get_aspect_dictionary():
    #             f.write(word + "\n")
    #
    #     with open("../../data/crf/list_unigrams.txt", 'w') as f:
    #         for word in cdg.get_list_unigrams():
    #             f.write(word + "\n")
