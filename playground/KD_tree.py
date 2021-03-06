import time
from timeit import default_timer as timer

import numpy as np
from sklearn.neighbors import KDTree

from src.indexing.utilities.metrics import mean_squared_error


# Makes the KD-Tree for fast lookup
def make_kd_tree(points, dim, i=0):
    if len(points) > 1:
        points.sort(key=lambda x: x[i])
        i = (i + 1) % dim
        half = len(points) >> 1
        return [
            make_kd_tree(points[:half], dim, i),
            make_kd_tree(points[half + 1:], dim, i), points[half]
        ]
    elif len(points) == 1:
        return [None, None, points[0]]


# def range_points(self, data, kd_node=None, i=0, upper_right, lower_left):
#     data_train = np.hstack((x_train, y_train))
#     data_train = data_train.tolist()
#     self.kdtree = self.build(data, dim = 2)
#     if kd_node is None:
#         kd_node = self.kdtree
#     if kd_node is not None:
#         if lower_left[i] <= kd_node[2][i] and  kd_node[2][i]>= upper_right[i]:
#             if lower_left
#             i = (i + 1) % dim
#         if lower_left[i] <= kd_node[2][i] and  kd_node[2][i]>= upper_right[i]:
#             pass
#             i = (i + 1) % dim


# Adds a point to the kd-tree
def add_point(kd_node, point, dim, i=0):
    if kd_node is not None:
        dx = kd_node[2][i] - point[i]
        i = (i + 1) % dim  # i is to alternate bw x and y
        for j, c in ((0, dx >= 0), (
                1, dx < 0
        )):  # j is for left and right addition  and c is to check where to add
            if c and kd_node[j] is None:
                kd_node[j] = [None, None, point]
            elif c:
                add_point(kd_node[j], point, dim, i)


def get_range(kd_node, area, i=0, out=None):

    if out == None:
        out = []
    if kd_node is not None:
        xmin, ymin, xmax, ymax = area

        # acceptance of point within range
        if kd_node[2][0] >= xmin and kd_node[2][0] <= xmax and kd_node[2][
                1] >= ymin and kd_node[2][1] <= ymax:
            out.append(kd_node[2])

        #for traversing left
        if (kd_node[2][i] >= xmin and i == 0) or (kd_node[2][i] >= ymin
                                                  and i == 1):
            get_range(kd_node[0], area, (i + 1) % 2, out)
        if (kd_node[2][i] >= xmin and i == 0) or (kd_node[2][i] >= ymin
                                                  and i == 1):
            get_range(kd_node[1], area, (i + 1) % 2, out)

    return out


# k nearest neighbors
def get_knn(kd_node,
            point,
            k,
            dim,
            dist_func,
            return_distances=True,
            i=0,
            heap=None):
    import heapq
    is_root = not heap
    if is_root:
        heap = []
    if kd_node is not None:
        dist = dist_func(point, kd_node[2])
        dx = kd_node[2][i] - point[i]
        if len(heap) < k:
            heapq.heappush(heap, (-dist, kd_node[2]))
        elif dist < -heap[0][0]:
            heapq.heappushpop(heap, (-dist, kd_node[2]))
        i = (i + 1) % dim
        # Goes into the left branch, and then the right branch if needed
        for b in [dx < 0] + [dx >= 0] * (
                dx * dx < -heap[0][0]
        ):  # dx*dx is r' and decide whether to check other branch or not.
            get_knn(kd_node[b], point, k, dim, dist_func, return_distances, i,
                    heap)
    if is_root:
        neighbors = sorted((-h[0], h[1]) for h in heap)
        return neighbors if return_distances else [n[1] for n in neighbors]


def test_recursion(a=[1, 4, 3, 2, 12, 11], i=0, out=None):
    if out == None:
        out = []
    if len(a) <= i:
        return out

    if a[i] % 2 == 0:
        out.append(a[i])
        out = test_recursion(a, i + 1, out)
    else:
        test_recursion(a, i + 1, out)

    return out


# For the closest neighbor
def get_nearest(kd_node,
                point,
                dim,
                dist_func,
                return_distances=True,
                i=0,
                best=None):
    if kd_node is not None:
        dist = dist_func(point, kd_node[2])
        dx = kd_node[2][i] - point[i]
        if not best:
            best = [dist, kd_node[2]]
        elif dist < best[0]:
            best[0], best[1] = dist, kd_node[2]
        i = (i + 1) % dim
        # Goes into the left branch, and then the right branch if needed
        for b in [dx < 0] + [dx >= 0] * (dx * dx < best[0]):
            get_nearest(kd_node[b], point, dim, dist_func, return_distances, i,
                        best)
    return best if return_distances else best[1]


def puts(l):
    for x in l:
        print(x)


def get_knn_naive(points, point, k, dist_func, return_distances=True):
    neighbors = []
    for i, pp in enumerate(points):
        dist = dist_func(point, pp)
        neighbors.append((dist, pp))
    neighbors = sorted(neighbors)[:k]
    return neighbors if return_distances else [n[1] for n in neighbors]


dim = 2

# def rand_point(dim):
#     return [random.uniform(-1, 1) for d in range(dim)]


def dist_sq(a, b, dim):
    return sum((a[i] - b[i])**2 for i in range(dim))


def dist_sq_dim(a, b):
    return dist_sq(a, b, dim)


def sklearn_kdtree(points, dim):
    dist = 0.0
    points = np.array(points)
    t_start1 = time.time()
    KDTree(points)
    t_end1 = time.time()
    print(t_end1 - t_start1, 'kd_tree sklearn')
    # s = pickle.dumps(tree)
    # tree_copy = pickle.loads(s)
    # dist, ind = tree.query(test, k=1)
    return dist**2


"""
Below is all the testing code
"""
if __name__ == "__main__":

    # filename=sys.argv[1]
    filename = "data/2d_lognormal_lognormal_20.csv"
    points = []
    # with open(filename, 'r') as csvfile:
    #     points_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    #     next(points_reader)
    #     for point in points_reader:
    #         points.append(list(np.float_(point[:2])))

    points = [[5, 6], [4, 2], [7, 9], [3, 1], [5, 5], [10, 7], [2, 11]]
    area = (2, 3, 6, 7)

    points = points
    test = [[3, 1]]
    result = []
    dim = 2

    t_start = time.time()
    start_time = timer()
    kd_tree = make_kd_tree(points, dim)
    end_time = timer()
    t_end = time.time()
    print(t_end - t_start, 'kd_tree')
    print(end_time - start_time, 'kd_tree time')
    # result.append(tuple(get_knn(kd_tree, [0] * dim, 2, dim, dist_sq_dim)))

    output = get_range(kd_tree, area)

    for t in test:
        result.append(tuple(get_knn(kd_tree, t, 5, dim, dist_sq_dim)))

    dis_grnd_truth = sklearn_kdtree(points, dim)

    print(result, "result")
    list_result = []
    print(len(result))
    for i in range(len(result[0])):
        list_result.append(result[0][i][0])

    print(list_result, 'list_result')
    # print(t_end-t_start, "Time taken")
    print(dis_grnd_truth[0], "dis_grnd_truth")
    mse_error = mean_squared_error(dis_grnd_truth[0],
                                   list_result,
                                   squared=False)
    print(mse_error, 'mse_error')

# def bench1():
#     kd_tree = make_kd_tree(points, dim)
#     for point in additional_points:
#         add_point(kd_tree, point, dim)
#     # result1.append(tuple(get_knn(kd_tree, [0] * dim, 1, dim, dist_sq_dim)))
#     for t in test:
#         result1.append(tuple(get_knn(kd_tree, t, 1, dim, dist_sq_dim)))

# def bench2():
#     all_points = points + additional_points
#     result2.append(tuple(get_knn_naive(all_points, [0] * dim, 8, dist_sq_dim)))
#     for t in test:
#         result2.append(tuple(get_knn_naive(all_points, t, 8, dist_sq_dim)))

# cProfile.run("bench1()")
# cProfile.run("bench2()")

# puts(result1[0])
# print("")
# puts(result2[0])
# print("")

# print("Is the result same as naive version?: {}".format(result1 == result2))

# print("")
# kd_tree = make_kd_tree(points, dim)

# print(get_nearest(kd_tree, [0] * dim, dim, dist_sq_dim))
