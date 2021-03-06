import csv
from timeit import default_timer as timer

import numpy as np
from scipy.spatial import KDTree as ScipyKDTree

import src.indexing.utilities.metrics as metrics


class ScipyKDTreeModel():
    def __init__(self, leafsize=1):
        super(ScipyKDTreeModel, self).__init__()
        self.name = 'Scipy KD-Tree'
        self.kdtree = None
        self.leafsize = leafsize
        self.y_train = None
        self.page_size = 1

    def train(self, x_train, y_train, x_test, y_test):

        #Build kd tree with train data
        start_time = timer()
        self.build(x_train)
        end_time = timer()
        build_time = end_time - start_time
        self.y_train = y_train
        self.x_train = x_train

        mse = 0.0
        y_predict_test = []
        # data_test=np.hstack((x_test, y_test))
        for key in x_test:
            pred = self.predict(key)
            y_predict_test.append(pred)
        mse = metrics.mean_squared_error(y_test, y_predict_test)

        return mse, build_time

    def predict_knn_query(self, key, k_nearest=1):

        dist, indx = self.kdtree.query(key, k=k_nearest)
        # y_predict = []
        # y_predict = np.array(self.y_train[indx])

        # y_predict = self.y_train[indx]

        return dist

    def predict(self, key, k_nearest=1):

        dist, indx = self.kdtree.query(key, k=k_nearest)

        y_predict = np.array(self.y_train[indx])

        return np.expand_dims(y_predict, axis=0)

    def build(self, x):
        self.kdtree = ScipyKDTree(x, leafsize=self.leafsize)

        return 0

    def get_storage(self):

        return self.kdtree


if __name__ == "__main__":
    filename = "data/2d_lognormal_lognormal_1000000.csv"
    points = []
    with open(filename, 'r') as csvfile:
        points_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        next(points_reader)
        for point in points_reader:
            points.append(list(np.float_(point[:2])))

    x_train = np.array(points)

    tree = ScipyKDTreeModel(leafsize=1)
    tree.build(x_train)
