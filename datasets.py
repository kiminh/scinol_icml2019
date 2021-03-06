#!/usr/bin/env python3

import os
import sys
import pickle
from distributions import *

from sklearn.model_selection import train_test_split
from preprocess import load_text

# from sklearn.metrics.pairwise import sigmoid_kernel

MNIST_DOWNLOAD_DIR = '/tmp/mnist_data/'
MNIST_LECUN_URL = "http://yann.lecun.com/exdb/mnist/"
MNIST_MIRROR_URL = 'https://storage.googleapis.com/cvdf-datasets/mnist/'
MNIST_URL = MNIST_MIRROR_URL

MNIST_TRAIN_IMAGES_FILENAME = 'train-images-idx3-ubyte.gz'
MNIST_TRAIN_LABELS_FILENAME = 'train-labels-idx1-ubyte.gz'
MNIST_TEST_IMAGES_FILENAME = 't10k-images-idx3-ubyte.gz'
MNIST_TEST_LABELS_FILENAME = 't10k-labels-idx1-ubyte.gz'
MNIST_DATA_SHAPE = (28, 28, 1)
MNIST_CLASSES_NUM = 10

UCI_DATASETS = "http://archive.ics.uci.edu/ml/machine-learning-databases"
UCI_MADELON = UCI_DATASETS + "/madelon/MADELON"
MADELON_TRAIN = UCI_MADELON + "/madelon_train.data"
MADELON_TRAIN_LABELS = UCI_MADELON + "/madelon_train.labels"
MADELON_TEST = UCI_MADELON + "/madelon_valid.data"
MADELON_TEST_LABELS = UCI_DATASETS + "/madelon/" + "madelon_valid.labels"

UCI_BANK_URL = UCI_DATASETS + "/00222/bank-additional.zip"

UCI_CENSUS_URL = UCI_DATASETS + "/census-income-mld/census.tar.gz"

UCI_COVTYPE_URL = UCI_DATASETS + "/covtype/covtype.data.gz"

UCI_CTSCAN_URL = UCI_DATASETS + "/00206/slice_localization_data.zip"

CIFAR_URL = 'https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz'
CIFAR_DOWNLOAD_DIR = '/tmp/cifar10_data'
CIFAR_EXTRACT_PATH = 'cifar-10-batches-py'
CIFAR_DATA_SHAPE = (32, 32, 3)
CIFAR_CLASSESS_NUM = 10

WNP_LINK = "https://cs.stanford.edu/people/karpathy/char-rnn/warpeace_input.txt"
WNP_DOWNLOAD_DIR = "/tmp/war_and_peace"
WNP_FILE = os.path.join(WNP_DOWNLOAD_DIR, "warpeace_input.txt")

PTB_LINK = "http://www.fit.vutbr.cz/~imikolov/rnnlm/simple-examples.tgz"
PTB_DOWNLOAD_LINK = "/tmp/penn_treebank"

REGRESSION = "regression"
CLASSIFICATION = "classification"
ACCEPED_TASKS = (CLASSIFICATION, REGRESSION)


def _to_one_hot(int_labels):
    from sklearn.preprocessing import OneHotEncoder
    enc = OneHotEncoder(categories='auto')
    return enc.fit_transform(int_labels.reshape([-1, 1])).toarray()


# TODO some regression tasks?
class _Dataset():
    def __init__(self,
                 name,
                 train_data,
                 test_data,
                 input_shape,
                 num_outputs,
                 train_batchsize=None,
                 test_batchsize=None,
                 convert_labels_to_one_hot=True,
                 seed=None,
                 sequential=False,
                 use_embeddings=False,
                 task=CLASSIFICATION,
                 **kwargs):
        # TODO check if one hot coverter is ok for all datasets
        if num_outputs == 2:
            convert_labels_to_one_hot = False
            num_outputs = 1

        if task not in ACCEPED_TASKS:
            raise ValueError("task should be in {}. is: {}".format(task, ACCEPED_TASKS))
        self.sequential = sequential
        self.use_embeddings = use_embeddings
        self._name = name
        self._input_shape = list(input_shape)
        self._outputs_num = num_outputs
        self.test = list(test_data)
        self.train = list(train_data)
        self.task = task
        self.one_hot_labels = convert_labels_to_one_hot

        if self.one_hot_labels:
            if sequential:
                raise NotImplementedError("Might now work correclty???")
            self.train[1] = _to_one_hot(self.train[1])
            self.test[1] = _to_one_hot(self.test[1])
        self.train_batchsize = train_batchsize
        self.test_batchsize = test_batchsize

        self.seeds = seed

    def get_name(self):
        return self._name

    @property
    def outputs_num(self):
        return self._outputs_num

    @property
    def size(self):
        return len(self.train[0]) + len(self.test[0])

    @property
    def input_shape(self):
        return self._input_shape

    @property
    def feature_scale(self):
        all_data = np.concatenate([self.train[0], self.test[0]], axis=0)
        flat_data = all_data.reshape(len(all_data), -1)
        # l2norm = ((flat_data ** 2).sum(0)) ** 0.5
        l2norm = np.linalg.norm(flat_data, axis=0)
        l2norm = l2norm[l2norm > 0]
        return l2norm.max() / l2norm.min()

    @property
    def feature_spread(self):
        all_data = np.concatenate([self.train[0], self.test[0]], axis=0)
        flat_data = all_data.reshape(len(all_data), -1)
        fmax = abs(flat_data).max(0)
        return fmax.max() / fmax[fmax != 0].min()

    def train_batches(self, batchsize=None):
        if batchsize is None:
            batchsize = self.train_batchsize

        x, y = self.train
        num_examples = len(x)

        # TODO seed support
        perm = np.random.permutation(num_examples)
        for ai in range(0, num_examples, batchsize):
            bi = min(ai + batchsize, num_examples)
            minibatch = x[perm[ai:bi]], y[perm[ai:bi]]
            yield minibatch

    def test_batches(self, batchsize=None):
        raise NotImplementedError()

    def get_test_data(self):
        return self.test

    def maybe_download(self, url, download_path):
        os.makedirs(download_path, exist_ok=True)

        filename = url.split('/')[-1]
        filepath = os.path.join(download_path, filename)
        if not os.path.exists(filepath):
            # TODO use tqdm
            def _progress(count, block_size, total_size):
                sys.stdout.write('\rDownloading %s %.1f%%' % (filename,
                                                              float(count * block_size) / float(
                                                                  total_size) * 100.0))
                sys.stdout.flush()

            from six.moves import urllib
            filepath, _ = urllib.request.urlretrieve(url, filepath, _progress)
            statinfo = os.stat(filepath)
            print()
            print('Successfully downloaded', filename, statinfo.st_size, 'bytes.')


class Cifar10(_Dataset):
    def __init__(self,
                 name="cifar10",
                 *args, **kwargs):
        print("Loading cifar10 dataset.")
        self.maybe_download_and_extract()
        train_data, test_data = self.load_dataset()
        super(Cifar10, self).__init__(name,
                                      train_data=train_data,
                                      test_data=test_data,
                                      input_shape=CIFAR_DATA_SHAPE,
                                      num_outputs=CIFAR_CLASSESS_NUM,
                                      *args, **kwargs)

    def maybe_download_and_extract(self):
        """Download and extract the tarball from Alex's website."""
        if not os.path.exists(CIFAR_DOWNLOAD_DIR):
            os.makedirs(CIFAR_DOWNLOAD_DIR)
        filename = CIFAR_URL.split('/')[-1]
        filepath = os.path.join(CIFAR_DOWNLOAD_DIR, filename)
        if not os.path.exists(filepath):
            def _progress(count, block_size, total_size):
                sys.stdout.write('\rDownloading %s %.1f%%' % (filename,
                                                              float(count * block_size) / float(total_size) * 100.0))
                sys.stdout.flush()

            from six.moves import urllib
            filepath, _ = urllib.request.urlretrieve(CIFAR_URL, filepath, _progress)
            print()
            statinfo = os.stat(filepath)
            print('Successfully downloaded', filename, statinfo.st_size, 'bytes.')
        extracted_dir_path = os.path.join(CIFAR_DOWNLOAD_DIR, CIFAR_EXTRACT_PATH)
        if not os.path.exists(extracted_dir_path):
            import tarfile
            tarfile.open(filepath, 'r:gz').extractall(CIFAR_DOWNLOAD_DIR)

    def load_dataset(self):
        train_filenames = [os.path.join(CIFAR_DOWNLOAD_DIR,
                                        CIFAR_EXTRACT_PATH,
                                        'data_batch_{}'.format(i))
                           for i in range(1, 6)]
        test_filename = os.path.join(CIFAR_DOWNLOAD_DIR,
                                     CIFAR_EXTRACT_PATH,
                                     'test_batch')
        train_images = []
        train_labels = []

        def process_images(ims):
            ims = ims.reshape([-1, 3, 32, 32]).astype(np.float32) / 255
            return np.transpose(ims, [0, 2, 3, 1])

        for filename in train_filenames:
            with open(filename, 'rb') as file:
                data = pickle.load(file, encoding='latin1')
                images = data['data']
                labels = data['labels']
                train_images.append(images)
                train_labels.append(labels)
        train_images = process_images(np.concatenate(train_images))
        train_labels = np.concatenate(train_labels).astype(np.int64)

        with open(test_filename, 'rb') as file:
            test_data = pickle.load(file, encoding='latin1')
            test_images = test_data['data']
            test_labels = test_data['labels']

        test_images = process_images(test_images)
        test_labels = np.int64(test_labels)

        return (train_images, train_labels), (test_images, test_labels)


class _Penn(_Dataset):
    def __init__(self,
                 name,
                 seed=None,
                 test_ratio=0.33,
                 *args, **kwargs):
        if seed is not None:
            raise NotImplementedError()

        # print("Fetching '{}' dataset. It may take a while.".format(name))
        download_path = "/tmp/penn_{}".format(name)
        os.makedirs(download_path, exist_ok=True)

        from pmlb import fetch_data
        x, y = fetch_data(name, return_X_y=True, local_cache_dir=download_path)
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)
        print(len(x_train))
        exit(0)
        num_outputs = len(np.unique(y))
        super(_Penn, self).__init__("Penn_" + name,
                                    train_data=(x_train, y_train),
                                    test_data=(x_test, y_test),
                                    input_shape=[x.shape[1]],
                                    num_outputs=num_outputs,
                                    seed=seed,
                                    *args, **kwargs)


class UCI_Madelon(_Dataset):
    def __init__(self,
                 name="UCI_Madelon",
                 *args, **kwargs):
        # print("Fetching Madelon dataset. It may take a while.")
        download_path = "/tmp/uci_madelon"

        def download_and_extract(url):
            self.maybe_download(url, download_path)
            file = os.path.join(download_path, url.split("/")[-1])
            return np.genfromtxt(file, delimiter=" ")

        x_train = download_and_extract(MADELON_TRAIN)
        x_test = download_and_extract(MADELON_TEST)
        y_train = (download_and_extract(MADELON_TRAIN_LABELS) + 1) / 2
        y_test = (download_and_extract(MADELON_TEST_LABELS) + 1) / 2

        num_outputs = 2  # len(np.unique(y))
        super(UCI_Madelon, self).__init__(name,
                                          train_data=(x_train, y_train),
                                          test_data=(x_test, y_test),
                                          input_shape=[x_train.shape[1]],
                                          num_outputs=num_outputs,
                                          *args, **kwargs)


class UCI_Bank(_Dataset):
    def __init__(self,
                 name="UCI_Bank",
                 test_ratio=0.33,
                 seed=None,
                 *args, **kwargs):
        # print("Fetching Bank dataset. It may take a while.")
        download_path = "/tmp/uci_bank"

        self.maybe_download(UCI_BANK_URL, download_path)
        file = os.path.join(download_path, UCI_BANK_URL.split("/")[-1])
        import zipfile
        zip_ref = zipfile.ZipFile(file, 'r')
        zip_ref.extractall(download_path)
        zip_ref.close()

        import pandas as pd
        csv_file = os.path.join(download_path, "bank-additional/bank-additional-full.csv")
        dataframe = pd.read_csv(csv_file, delimiter=";")

        y = np.zeros_like(dataframe["y"], dtype=np.int32)
        y[dataframe["y"] == "yes"] = 1
        dataframe.drop("y", axis=1, inplace=True)
        dataframe = pd.get_dummies(dataframe, drop_first=True)
        x = np.float32(dataframe.values)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)

        num_outputs = 2  # len(np.unique(y))
        super(UCI_Bank, self).__init__(name,
                                       train_data=(x_train, y_train),
                                       test_data=(x_test, y_test),
                                       input_shape=[x_train.shape[1]],
                                       num_outputs=num_outputs,
                                       *args, **kwargs)


class UCI_Census(_Dataset):
    def __init__(self,
                 name="UCI_Census",
                 test_ratio=0.33,
                 seed=None,
                 *args, **kwargs):
        # print("Fetching Census dataset. It may take a while.")
        download_path = "/tmp/uci_census"

        self.maybe_download(UCI_CENSUS_URL, download_path)

        targzfile = os.path.join(download_path, UCI_CENSUS_URL.split("/")[-1])

        import tarfile
        tar = tarfile.open(targzfile, mode="r")
        tar.extractall(download_path)
        tar.close()
        os.chmod(download_path + "/census-income.names", 0o770)
        os.chmod(download_path + "/census-income.data", 0o770)
        os.chmod(download_path + "/census-income.test", 0o770)
        import pandas as pd

        train_x = pd.read_csv(download_path + "/census-income.data", header=None, delimiter=",")
        test_x = pd.read_csv(download_path + "/census-income.test", header=None, delimiter=",")

        labels_column = 41
        x = pd.concat([train_x, test_x], axis=0)
        y = np.zeros_like(x[labels_column], dtype=np.int32)
        y[x[labels_column] == " 50000+."] = 1
        x.drop(labels_column, axis=1, inplace=True)

        x_object = x.select_dtypes(include=['object']).copy()
        x_numerical = x.select_dtypes(exclude=['object']).copy()

        x_object = pd.get_dummies(x_object, drop_first=True)

        x = pd.concat([x_numerical, x_object], axis=1)
        x = np.float32(x.values)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)
        num_outputs = 2  # len(np.unique(y))
        super(UCI_Census, self).__init__(name,
                                         train_data=(x_train, y_train),
                                         test_data=(x_test, y_test),
                                         input_shape=[x_train.shape[1]],
                                         num_outputs=num_outputs,
                                         *args, **kwargs)


class UCI_Covertype(_Dataset):
    def __init__(self,
                 name="UCI_Covertype",
                 test_ratio=0.33,
                 seed=None,
                 *args, **kwargs):
        # print("Fetching Census dataset. It may take a while.")
        download_path = "/tmp/uci_covertype"

        self.maybe_download(UCI_COVTYPE_URL, download_path)

        file = os.path.join(download_path, UCI_COVTYPE_URL.split("/")[-1])

        import gzip
        import pandas as pd
        gzfile = gzip.open(file, 'rb')
        x = pd.read_csv(gzfile, delimiter=",", header=None)

        label_column = 54
        y = np.int32(x[label_column].values)
        x.drop(label_column, axis=1, inplace=True)
        x = np.float32(x.values)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)

        num_outputs = len(np.unique(y))
        super(UCI_Covertype, self).__init__(name,
                                            train_data=(x_train, y_train),
                                            test_data=(x_test, y_test),
                                            input_shape=[x_train.shape[1]],
                                            num_outputs=num_outputs,
                                            *args, **kwargs)


class UCI_CTScan(_Dataset):
    def __init__(self,
                 name="UCI_CTScan",
                 test_ratio=0.33,
                 seed=None,
                 *args, **kwargs):
        # print("Fetching Bank dataset. It may take a while.")
        download_path = "/tmp/uci_ctscan"

        self.maybe_download(UCI_CTSCAN_URL, download_path)
        file = os.path.join(download_path, UCI_CTSCAN_URL.split("/")[-1])
        import zipfile
        zip_ref = zipfile.ZipFile(file, 'r')
        zip_ref.extractall(download_path)
        zip_ref.close()

        import pandas as pd
        csv_file = os.path.join(download_path, "slice_localization_data.csv")
        dataframe = pd.read_csv(csv_file, delimiter=",")

        # print(dataframe.shape)
        # exit(0)
        y = np.float32(dataframe["reference"].values).reshape((-1, 1))
        dataframe.drop("reference", axis=1, inplace=True)
        dataframe = pd.get_dummies(dataframe, drop_first=True)
        x = np.float32(dataframe.values)

        # scaler = StandardScaler()
        # x = scaler.fit_transform(x)
        # y = scaler.fit_transform(y)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)

        num_outputs = 2  # len(np.unique(y))
        super(UCI_CTScan, self).__init__(name,
                                         convert_labels_to_one_hot=False,
                                         task=REGRESSION,
                                         train_data=(x_train, y_train),
                                         test_data=(x_test, y_test),
                                         input_shape=[x_train.shape[1]],
                                         num_outputs=num_outputs,
                                         *args, **kwargs)


class Mnist(_Dataset):
    def __init__(self, *args, **kwargs):
        mnist_files = [MNIST_TRAIN_IMAGES_FILENAME,
                       MNIST_TRAIN_LABELS_FILENAME,
                       MNIST_TEST_IMAGES_FILENAME,
                       MNIST_TEST_LABELS_FILENAME]

        for filename in mnist_files:
            self.maybe_download(MNIST_URL + filename, MNIST_DOWNLOAD_DIR)

        # print("Loading mnist data ...")
        from mnist import MNIST
        mnist_loader = MNIST(MNIST_DOWNLOAD_DIR)
        mnist_loader.gz = True
        train_images, train_labels = mnist_loader.load_training()
        test_images, test_labels = mnist_loader.load_testing()
        process_images = lambda im: (np.array(im).astype(np.float32) / 255.0).reshape((- 1, 28, 28, 1))

        train_images = process_images(train_images)
        test_images = process_images(test_images)
        train_labels = np.int64(train_labels)
        test_labels = np.int64(test_labels)

        super(Mnist, self).__init__(name="mnist",
                                    train_data=(train_images, train_labels),
                                    test_data=(test_images, test_labels),
                                    input_shape=MNIST_DATA_SHAPE,
                                    num_outputs=MNIST_CLASSES_NUM,
                                    *args, **kwargs)


class Synthetic(_Dataset):
    def __init__(self,
                 name="normal",
                 size=100000,
                 num_features=21,
                 test_ratio=0.33,
                 seed=None,
                 distribution=normal_scaled,
                 **kwargs):
        x, labels = distribution(
            size,
            num_features,
            loc=0,
            seed=seed)

        x_train, x_test, y_train, y_test = train_test_split(x, labels, test_size=test_ratio, random_state=seed)

        super(Synthetic, self).__init__(
            name=name,
            train_data=(x_train, y_train),
            test_data=(x_test, y_test),
            input_shape=[num_features],
            num_outputs=2,
            **kwargs)


class SyntheticRegression(_Dataset):
    def __init__(self,
                 name="normal_reg",
                 size=10000,
                 num_features=61,
                 test_ratio=0.5,
                 seed=None,
                 distribution=normal,
                 **kwargs):
        x, _ = distribution(
            size,
            num_features=num_features,
            loc=0.0,
            scale=1.0,
            seed=seed)
        # scales = np.std(x, 0)
        y = (x).sum(axis=1).reshape((-1, 1))
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=seed)
        super(SyntheticRegression, self).__init__(
            name=name,
            train_data=(x_train, y_train),
            test_data=(x_test, y_test),
            input_shape=[num_features],
            num_outputs=2,
            task=REGRESSION,
            **kwargs)


class SyntheticStandardized(Synthetic):
    def __init__(self,
                 name="normal_standardized",
                 **kwargs):
        super(SyntheticStandardized, self).__init__(
            name=name,
            **kwargs)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        self.train[0] = scaler.fit_transform(self.train[0])
        self.test[0] = scaler.transform(self.test[0])


class _CharText(_Dataset):
    def __init__(self,
                 link,
                 file,
                 download_dir,
                 name,
                 test_ratio=0.2,
                 seed=None,
                 seq_len=50,
                 *args,
                 **kwargs):
        self.maybe_download(link, download_dir)
        train, test, token_to_idx = load_text(file, test_frac=test_ratio)
        self.token_to_idx = token_to_idx
        self.idx_to_token = {v: k for k, v in token_to_idx.items()}
        self.tokens_num = len(token_to_idx)
        train = train[0:len(train) - len(train) % seq_len + 1]
        test = test[0:len(test) - len(test) % seq_len + 1]
        x_train = train[:-1].reshape((-1, seq_len))
        y_train = train[1:].reshape((-1, seq_len))
        x_test = test[:-1].reshape((-1, seq_len))
        y_test = test[1:].reshape((-1, seq_len))
        super(_CharText, self).__init__(
            name=name,
            train_data=(x_train, y_train),
            test_data=(x_test, y_test),
            input_shape=[seq_len],
            num_outputs=self.tokens_num,
            convert_labels_to_one_hot=False,
            sequential=True,
            use_embeddings=True,
            **kwargs)


class WarAndPeace(_CharText):
    def __init__(self, *args, **kwargs):
        super(WarAndPeace, self).__init__(
            link=WNP_LINK,
            file=WNP_FILE,
            download_dir=WNP_DOWNLOAD_DIR,
            name="warandpeace",
            *args, **kwargs)


SynthScaled = lambda **kwargs: Synthetic(
    name="art_scaled",
    size=10000,
    test_ratio=0.8,
    distribution=normal_scaled,
    **kwargs)
SynthOutliers = lambda **kwargs: Synthetic(
    name="art_outliers",
    distribution=normal_dist_outliers,
    **kwargs)


Artificial = lambda **kwargs: Synthetic(
    name="artificial",
    size=105000,
    test_ratio=0.9523809523809523,
    distribution=normal_scaled,
    **kwargs)
SynthReg = lambda **kwargs: SyntheticRegression(**kwargs)

PennPoker = lambda **kwargs: _Penn("poker", **kwargs)
PennFars = lambda **kwargs: _Penn("fars", **kwargs)
PennKddcup = lambda **kwargs: _Penn("kddcup", **kwargs)
PennConnect4 = lambda **kwargs: _Penn("connect-4", **kwargs)
PennShuttle = lambda **kwargs: _Penn("shuttle", **kwargs)
PennSleep = lambda **kwargs: _Penn("sleep", **kwargs)
