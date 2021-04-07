import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def visualize(dist_name,filename):
    data = pd.read_csv(filename)
    x = data.iloc[:, :-1].values
    y = data.iloc[:, 1].values
    plt.scatter(x, y, s=np.pi*3, alpha=0.5)
    plt.title('x-y of {} distribution'.format(dist_name))
    plt.xlabel('x')
    plt.ylabel('y')
    plt.show()

if __name__=="__main__":
    filename = sys.argv[1]
    distribution = filename.split("_")[1]
    visualize(distribution, filename)