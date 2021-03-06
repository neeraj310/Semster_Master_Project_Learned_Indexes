# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 14:36:30 2021

@author: neera
"""
import sys
from timeit import default_timer as timer
from typing import List, Tuple
import numpy as np
import pandas as pd
from src.indexing.models import BaseModel
import src.indexing.utilities.metrics as metrics

import matplotlib.pyplot as plt

class LisaModel():
    def __init__(self, cellSize, nuOfShards) -> None:
        #cellSize : Nu of cells into which key space is divided
        self.cellSize = cellSize
        # keysPerShard : Number of keys per shard(\Psi)
        self.keysPerShard = 0
        # Np Array to contain the key value pairs
        self.train_array=0
        # Np Array to store cell boundaries for each cell. 
        self.cellMatrix=0
        # keysPerCell : Numebr of keys per Cell. 
        self.keysPerCell=0
        # nuOfKeys : Total nu of points in the training database
        self.nuOfKeys=0
        '''
        additionalKeysInLastCell : Last cell may have more keys than keysPerCell
        Bookkeeping code to allow for arbotary values of cell Size instead of
        factor of nuOfKeys.
        '''
        self.additionalKeysInLastCell =0
        # Number of Intervals into which sorted mapped values are divided
        # Shard Prediction Function is learned for each interval. 
        self.nuOfIntervals = 0
        self.numOfKeysPerInterval = 0
        # Number of shards per interval 
        self.nuOfShards=nuOfShards
        # Placeholder to store information regarding shard training function
        self.shardMatrix=0
        # Placeholder to store mapped values boundaries boundaries for each interval
        self.mappedIntervalMatrix = 0
        # Additional logic to allow arbitary values for nuOfIntervals
        self.keysInLastInterval=0
        # shardPredictionErrorCount : Additional debug error counter
        self.shardPredictionErrorCount = 0
        self.page_size=1
        self.name = 'Lisa'
        self.initDelta = 3
        self.debugPrint = 0
        print('In Lisa Model')
    
    '''
       Generates grid cells from training data. Divides training data into
       cellSize*cellSize nu of cells. 
    
       Parameters
        ----------
         self.train_array : Np array
             Array containing key value pairs
       
        Attributes :  
        -------
         self.cellMatrix: Np Array
             Initialize an NP array to store bookkeeping infromation for cell grid, like
             cell boundaries, cell number, area of the cell. 
        
    '''  
    def generate_grid_cells(self):
        cellSize =  self.cellSize
        self.nuOfKeys = self.train_array.shape[0]
        self.keysPerCell =  self.nuOfKeys // (cellSize*cellSize)
        keysPerCell = self.keysPerCell
        self.additionalKeysInLastCell = self.nuOfKeys-(keysPerCell*cellSize*cellSize)
        
        
        self.numOfKeysPerInterval = self.keysPerCell
        self.nuOfIntervals = self.nuOfKeys // self.numOfKeysPerInterval
        self.keysInLastInterval = self.nuOfKeys - self.numOfKeysPerInterval*(self.nuOfIntervals -1)

        self.keysPerShard = self.numOfKeysPerInterval//self.nuOfShards
        self.nuOfKeysToSearchinAdjacentShard = self.keysPerShard //6
        if(self.nuOfKeysToSearchinAdjacentShard < 5):
            self.nuOfKeysToSearchinAdjacentShard= 5
        if (self.nuOfKeysToSearchinAdjacentShard >self.keysPerShard ):
            print('Invalid Configuration')
            return -1
        self.shardMatrix = np.zeros((self.nuOfIntervals, 5))
        if(self.debugPrint):
            print('nuOfIntervals =%d, numOfKeysPerInterval = %d nuOfShards = %d keysperShard = %d NuofKeys = %d keysInLastInterval = %d'
                      %(self.nuOfIntervals, self.numOfKeysPerInterval,self.nuOfShards,self.keysPerShard, self.nuOfKeys, self.keysInLastInterval) )

            print('cellSize = %d, keysPerCell = %d, nuOfKeys = %d additionalKeysInLastCell = %d' %(cellSize, keysPerCell,  self.nuOfKeys, self.additionalKeysInLastCell ))
        # Sore keys based on x dimension
        self.train_array = self.train_array[self.train_array[:,0].argsort()]
        '''
        Initialize Cell Matrix, Each element of cell matrix has [(l0, u0 ), (l1, u1), 
        Cell Id, CellId*keysPerCell]. We  keep cell id and CellId*keysPerCell in 
        2 mappings,position 5, 6, is mapping value increasing in x direction
        position 7 8 is , mapping value increasing in y direction. 
        '''
        self.cellMatrix = np.zeros((cellSize*cellSize, 9))
        # Divie X axis into equal no of keys, and fill x values for the cell
        for i in range( self.cellSize):
            for j in range( self.cellSize):
                # Save x coordinate of first key in the cell
                self.cellMatrix[i*cellSize+j][0] =  self.train_array[(keysPerCell*cellSize*(j))-(not(not(j%cellSize))) ,0]
                # Save x coordinate of last key in the cell
                self.cellMatrix[i*cellSize+j][2] =  self.train_array[(keysPerCell*cellSize*(j+1)) -1 ,0]
                self.cellMatrix[i*cellSize+j][4] =  i*cellSize+j
                self.cellMatrix[i*cellSize+j][5] =  (keysPerCell*cellSize*i)+j*keysPerCell
                self.cellMatrix[i*cellSize+j][6] =  i + cellSize*j
                self.cellMatrix[i*cellSize+j][7] =  (i*keysPerCell)+(keysPerCell*cellSize*j)
        # Last cell may have more keys than KeysPerCell
        self.cellMatrix[i*cellSize+j][2] =  self.train_array[-1 ,0]
        
        # Sort Keys along y direction
        for i in range(cellSize-1):
            self.train_array[keysPerCell*cellSize*i:keysPerCell*cellSize*(i+1)] = \
                       self.train_array[(self.train_array[keysPerCell*cellSize*i:keysPerCell*cellSize*(i+1),1].argsort())+keysPerCell*cellSize*i]
        # Last cell may have more keys than KeysPerCell 
        i = i+1
        self.train_array[keysPerCell*cellSize*i:-1] = self.train_array[(self.train_array[keysPerCell*cellSize*i:-1,1].argsort())+keysPerCell*cellSize*i]
   
        # Divide the keys along y Axis
        for i in range(cellSize):
            for j in range(cellSize):
                self.cellMatrix[i*cellSize+j][1] =  self.train_array[((keysPerCell*(i-1)) + (keysPerCell*cellSize*j) +(keysPerCell-1)) ,1]
                self.cellMatrix[i*cellSize+j][3] =  self.train_array[((keysPerCell*i) + (keysPerCell*cellSize*j) +(keysPerCell-1)) ,1]
                #print(((keysPerCell*(i-1)) + (keysPerCell*cellSize*(j)) +(keysPerCell-1)))
                #print( ((keysPerCell*(i)) + (keysPerCell*cellSize*(j)) +(keysPerCell-1)))
                self.cellMatrix[i*cellSize+j][8] =  ((self.cellMatrix[i*cellSize+j][3] - self.cellMatrix[i*cellSize+j][1])* \
                                (self.cellMatrix[i*cellSize+j][2] - self.cellMatrix[i*cellSize+j][0]))

        self.cellMatrix[i*cellSize+j][3] =  self.train_array[-1 ,1]
        self.cellMatrix[i*cellSize+j][8] =  ((self.cellMatrix[i*cellSize+j][3] - self.cellMatrix[i*cellSize+j][1])*
                                        (self.cellMatrix[i*cellSize+j][2] - self.cellMatrix[i*cellSize+j][0]))
        # Bookkeeping code        
        for i in range(cellSize):
            self.cellMatrix[i][1] =  0
            self.cellMatrix[i][8] =  np.abs((self.cellMatrix[i][3] - self.cellMatrix[i][1])* \
                                           (self.cellMatrix[i][2] - self.cellMatrix[i][0]))
      
        return 0
    
    '''
       Apply mapping function to the 2 dimensional key value
    
       Attributes :  
        -------
        self.cellMatrix: Np Array
             Containing bookkeeping infromation for cell grid, like
             cell boundaries, cell number, area of the cell. 
             
        self.train_array: Np Array
           Np Array containg key value pair. Mapped value will be calculated
           for each key value pair in the training array.
        
        
        
    '''  
    def compute_mapping_value(self):
        j = 0
        k = 0
        # Apply mapping function to each key in the training database
        for i in range(0,(self.keysPerCell*self.cellSize*self.cellSize)):
            idx = (((i% self.keysPerCell)))
            cellIdx = j*self.cellSize +k
            keyArea = ((self.train_array[i][1] - self.cellMatrix[cellIdx][1])* \
                      (self.train_array[i][0] - self.cellMatrix[cellIdx][0]))
     
            self.train_array[i, 3] =   self.cellMatrix[cellIdx][7] + \
                                       ((keyArea/self.cellMatrix[cellIdx][8])*self.keysPerCell)
          
            if(idx ==(self.keysPerCell -1) ):
                j  = j+1
                if(j == self.cellSize):
                    k = k+1
                    j = 0
                    
        # Last cell can contain additional keys. Handle this boundary condition             
        for i in range((self.keysPerCell*self.cellSize*self.cellSize), self.nuOfKeys):
            if(self.debugPrint):
                print('i = %d, cellIdx = %d' %(i,cellIdx ))
            keyArea = ((self.train_array[i][1] - self.cellMatrix[cellIdx][1])* \
                       (self.train_array[i][0] - self.cellMatrix[cellIdx][0]))
            self.train_array[i, 3] =   self.cellMatrix[cellIdx][7] + \
                                       ((keyArea/self.cellMatrix[cellIdx][8])*(self.keysPerCell+self.additionalKeysInLastCell))            
        # Sort the input data array with mapped values
        self.train_array = self.train_array[self.train_array[:,3].argsort()]   
    
    '''
        Convert input data to np array
    '''
    def convert_to_np_array(self, input_):
        if isinstance(input_, np.ndarray) is False:
            input_ = np.array(input_)
        return input_
   
    
   
    '''
        Return whether input matrix is Positive deifnite or not. 
    '''
    def is_pos_def(x):
        return np.all((np.around(np.linalg.eigvals(x),4)) >= 0)
   
    
   
    '''
        Get Initial set of betas
        Parameters
        ----------
        input_ : array_like
            The object containing mapped values for the interval.
        V : Integer
            Repersents the nu of keys in the interval
        D : Integer
            Nu of shards(line segments/slopes-intercepts values) needs to be learned from training data
    
        Returns
        -------
        b_ : numpy array
            The x(mapped value) locations where each line segment terminates. Referred to 
            as breakpoints for each line segment and should be structured as a 1-D numpy array.
    '''
    def get_betas(self,input_, V, D):
        b_ = np.zeros( D +1)
        b_[0], b_[-1] = np.min(input_), np.max(input_)
        i = 1
        while(i<(D)):
            b_[i] = input_[i*(V//D)]
            #print(i*(V//D))
            i = i+1            
            
        return b_
    
    
    
    '''
        Assemble the matrix A
        Parameters
        ----------
        betas : np array
            The x(mapped value) locations where each line segment terminates. Referred to 
            as breakpoints for each line segment and should be structured as a 1-D numpy array.
        x : np array
            The x locations which the linear regression matrix is assembled on.
            This must be a numpy array!
        Returns
        -------
        A : ndarray (2-D)
            The assembled linear regression matrix.
 
    '''
    def assemble_regression_matrix(self,betas, x):
        betas = self.convert_to_np_array(betas)
        # Sort the betas
        betas_order = np.argsort(betas)
        betas = betas[betas_order]
        # Fetch number of parameters and line segments
        n_segments = len(betas) - 1

        # Assemble the regression matrix
        A_list = [np.ones_like(x)]
        A_list.append(x - betas[0])
        for i in range(n_segments - 1):
            A_list.append(np.where(x >= betas[i+1],
                                       x - betas[i+1],
                                       0.0))
        A = np.vstack(A_list).T
        return A, betas,n_segments
    
    
    
    '''
        Compute line segments slope after a piecewise linear
        function has been fitted.
        This will also calculate the y-intercept from each line in the form
        y = mx + b. 
        Parameters
        ----------
        y_hat : np array
            Predicted value of the Sharding Function
        betas : np array
            The x locations which the linear regression matrix is assembled on.
            This must be a numpy array!
        n_segments
            Number of line segments to learn
            
        Returns
        -------
        slopes : ndarray(1-D)
            The slope of each ling segment as a 1-D numpy array.Slopes[0] is the slope
            of the first line segment.
        Intercepts : ndarray(1-D)
            The intercept of each ling segment as a 1-D numpy array.Intercept[0] is the slope
            of the first line segment.
    '''
    def compute_slopes(self, y_hat,betas,n_segments):
        slopes = np.divide(
                    (y_hat[1:n_segments + 1] -
                     y_hat[:n_segments]),
                    (betas[1:n_segments + 1] -
                     betas[:n_segments]))
        intercepts = y_hat[0:-1] - slopes * betas[0:-1]
        return slopes, intercepts
    
    
    '''
        Compute least square fit(alphas) for the A matrix
        This will also calculate the y-intercept from each line in the form
        y = mx + b. 
        Parameters
        ----------
        A : np array(2-D)
            Assembled Linear Regression Matrix
        y_data : np array 
            Array conatinaing the label values
           
            
        Returns
        -------
        alpha : ndarray(1-D)
           Cofficients of Least square solution
        SSR : Float
            Cost value at the Least square solution
        r:  ndarray(1-D)
            Residual Error
    '''
    def lstsq(self,A, y_gt):

        alpha, ssr, _, _ = np.linalg.lstsq(A, y_gt, rcond = -1)
        # ssr is only calculated if self.n_data > self.n_parameters
        # in this case we ll need to calculate ssr manually
        # where ssr = sum of square of residuals
        y_hat = np.dot(A, alpha)
        e = y_hat - y_gt
        n_parameters = A.shape[1]
        n_data = y_gt.size
        if n_data <= n_parameters:
            ssr = np.dot(e, e)
        if isinstance(ssr, list):
            ssr = ssr[0]
        elif isinstance(ssr, np.ndarray):
            if ssr.size == 0:
                y_hat = np.dot(A, alpha)
                e = y_hat - y_gt
                ssr = np.dot(e, e)
            else:
                ssr = ssr[0]

        return alpha,np.around(ssr, 3), e  
    
    
    
    '''
        Predict Shard Id. 
        Parameters
        ----------
        x : np array(2-D)
            Mapped Values Array
        alpha : np array 
            Least square solution cofficients
        betas : np array 
            Array containing termination point for line segments
             
        Returns
        -------
        y_hat : ndarray(1-D)
           Predicted value of Least square solution
    '''
    def predictShardId(self, x, alpha=None, betas=None):
        
        #print('in function predictShardId')
        if alpha is not None and betas is not None:
            #print(betas)
            alpha = alpha
            # Sort the betas, then store them
            betas_order = np.argsort(betas)
            #   print(betas_order)
            betas = betas[betas_order]
          
        x = self.convert_to_np_array(x)

        A,_,_ = self.assemble_regression_matrix(betas, x)

        # solve the regression problem
        y_pred = np.dot(A, alpha)
        return y_pred



    '''
        Calculate gradient update for beta(breakpoints)
        Parameters
        ----------
        x : np array(2-D)
            Mapped Values Array
        alpha : np array 
            Least square solution cofficients
        betas : np array 
            Array containing termination point for line segments
        r_error : np array 
           Error Residual from least square solutiuon
        n_segments : Interger
            Number of line segments(Shard Id) to learn
        Returns
        -------
        s : ndarray(1-D)
           Gradient update for next iteration 
    '''
    def calc_gradient(self, x, alpha, betas,r_error,n_segments):
        K = np.diag(alpha)
        G_list = [np.ones_like(x)]
        G_list.append(x - betas[0])
        for i in range(n_segments - 1):
            G_list.append(np.where(x >= betas[i+1],
                                   x - betas[i+1],
                                   np.inf))
        G = np.vstack(G_list)
        G= ((G!=np.inf).astype(int)*(-1))
        KG = np.dot(K, G)
        g= 2*(KG.dot(r_error))
        g = np.around(g,3)
        Y = 2*(KG.dot(np.transpose(KG)))
        Y = np.around(Y,3)
        try:
            Y_inverse = np.linalg.inv(Y)
            s = -Y_inverse.dot(g)
        except np.linalg.LinAlgError:
            if self.debugPrint:
                print('Y_inverse not avaliable')
            s = 0
        pass
        
        return s
    
    '''
        Find best learning rate( minimizes the ssr) for the iteration. 
        Parameters
        ----------
        s : np array
           gradient update
        betas : np array 
            Array containing termination point for line segments
        x : np array
            The x locations which the linear regression matrix is assembled on.
            
        y : np array 
            Array conatinaing the label values
        Returns
        -------
        lr : float
           learning rate to be used for iteration. 
    '''
    
 

    def find_learning_rate(self,s,betas,x, y):
        lr_list = [0.001, 0.1]
        ssr_list = []
        # Do parameter search for learning rate. 
        for lr in lr_list:
            betas_new = betas+lr*s
            A, _,_ =  self.assemble_regression_matrix(betas_new, x)
            alpha, ssr,r_error = self.lstsq(A, y)
            ssr_list.append(ssr)
        min_lr = ssr_list.index(min(ssr_list))
        lr = lr_list[min_lr]
        # Return learning rate whcih minimizes the ssr. 
        return lr
    
    '''
       Check  alpha constraint according to shard training section in the 
       lisa paper.(Section 3.4, equation (5))
    '''
    def check_alpha_constraint(self, alpha):
        flag = True
        for i in range(alpha.size+1):
            alpha_sum = 0
            for j in range(i):
              alpha_sum = alpha_sum+alpha[j]
            if (alpha_sum < 0):
                flag = False
                break
        
        return flag
    
    '''
      Plot learned value againt grounttruth for shard prediction
    '''

    def plot_sharding_prediction(self, x, y, alpha, betas):
        return
        xHat = np.linspace(min(x), max(x), num=10000)
        yHat = self.predictShardId(xHat, alpha,betas)
        plt.figure()
        plt.plot(x, y, '--')
        plt.plot(xHat, yHat, '-')
        plt.show()
        return

    '''
        Train linear functions for shard prediction. This function will be 
        called for each mapped interval. 
        Parameters
        ----------
        x : np array
            The x locations which the linear regression matrix is assembled on.
            
        y : np array 
            Array conatinaing the label values
        
        nuOfShards : Integer
            Number of linde segments to be learned. 
        Returns
        -------
        alpha : np array 
            Least square solution cofficients
        betas : np array 
            Array containing termination point for line segments
    '''
    def trainShardingLinearFunctions(self,x, y,nuOfShards):
        
        betas_list = []
        learning_iter_list= []
        early_stop_count = 0
        x_data, y_data = self.convert_to_np_array(x), self.convert_to_np_array(y)
        n_data = x_data.size
        #Initialize betas with uniform distribution
        betas = self.get_betas(x_data,n_data,nuOfShards)
       
        A, betas,n_segments = self.assemble_regression_matrix(betas, x_data)
       
        
        alpha, ssr_0,r_error = self.lstsq(A, y_data)
        betas_list.append(betas)
        learning_iter_list.append(ssr_0)
        self.plot_sharding_prediction(x_data, y_data, alpha, betas)
        #Training Loop
        itr = 0
        while(itr<1000):
            # Calculate Gradient Update
            s = self.calc_gradient(x_data, alpha, betas,r_error,n_segments)
            # Find best learning rate for this iter
            lr = self.find_learning_rate(s,betas,x_data, y_data)
            # Update betas 
            betas = betas+lr*s
            # Update alpha 
            A, betas,n_segments = self.assemble_regression_matrix(betas, x_data)
            alpha, ssr,r_error = self.lstsq(A, y_data)
            alpha_constraint = self.check_alpha_constraint(alpha)
            #Stop training if alpha constraint is violated
            if (alpha_constraint == False):
                break
            # Check for early stopping
            if (learning_iter_list[-1] == ssr):
                early_stop_count = early_stop_count+1
                if(early_stop_count > 4):
                    #print('Early Stopping')
                    break
            else:
                early_stop_count = 0
            learning_iter_list.append(ssr)
            betas_list.append(betas)
            itr = itr+1
           
        #get index corresponding to lowest error
        min_ssr = learning_iter_list.index(min(learning_iter_list))
        # get betas corresponding to lowest error
        betas =  np.array(betas_list[min_ssr])
        #get alphas corresponidng to lowest error
        A, betas,_ = self.assemble_regression_matrix(betas, x_data)
        alpha, ssr,r_error = self.lstsq(A, y_data)
        self.plot_sharding_prediction(x_data, y_data, alpha, betas)
        #print('Time taken %f' %(timer()-start_time))
        #print("Initial ssr %f, final ssr %f" %(ssr_0,ssr))
        return alpha, betas
    
    
    '''
        BookKeeping code to maintain mapped value at mapped interval boundries. 
        Attribues
        ----------
        self. mappedIntervalMatrix : np array
           Initializes a data structure with mapped values at boundaries of 
           mapped interval. 
            
       
    '''
    def createMappedIntervalMatrix(self):
        self.mappedIntervalMatrix = np.zeros((self.nuOfIntervals, 5))
        for i in range(self.nuOfIntervals-1):
            self.mappedIntervalMatrix[i][0] = i+1
            self.mappedIntervalMatrix[i][1] = self.train_array[i*self.numOfKeysPerInterval, 2]
            self.mappedIntervalMatrix[i][2] = self.train_array[(((i+1)*self.numOfKeysPerInterval)-1), 2]
            self.mappedIntervalMatrix[i][3] = self.train_array[i*self.numOfKeysPerInterval, 3]
            self.mappedIntervalMatrix[i][4] = self.train_array[(((i+1)*self.numOfKeysPerInterval)-1), 3]
            
        #Last Interval may have less nu of keys
        i = i+1
        self.mappedIntervalMatrix[i][0] = i+1
        self.mappedIntervalMatrix[i][1] = self.train_array[i*self.numOfKeysPerInterval, 2]
        self.mappedIntervalMatrix[i][2] = self.train_array[self.nuOfKeys-1, 2]
        self.mappedIntervalMatrix[i][3] = self.train_array[i+1*self.numOfKeysPerInterval, 3]
        self.mappedIntervalMatrix[i][4] = self.train_array[self.nuOfKeys-1, 3]
        
    
    '''
        BookKeeping code to maintain mapped value at Shard boundries. 
        Attribues
        ----------
        self.shardMatrix : np array
           Initializes a data structure with mapped values at boundaries of 
           shard intervals.
            
       
    '''
    
    def createShardMappingMatrix(self):
        self.shardMatrix = np.zeros((self.nuOfIntervals*self.nuOfShards, 5))
        numOfKeysPerInterval = self.numOfKeysPerInterval
        keysPerShard = self.keysPerShard
        # Initialize shardMatrix for ShardFunctions for each Interval. 
        for i in range(self.nuOfIntervals-1):
            for j in range(self.nuOfShards-1):
                # Store mapped values at shard interval boundaries.  
                idx = i*self.nuOfShards+j
                self.shardMatrix[idx][0] = idx+1
                self.shardMatrix[idx][1] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 2]
                self.shardMatrix[idx][2] = self.train_array[i*numOfKeysPerInterval+((j+1)*keysPerShard)-1, 2]
                self.shardMatrix[idx][3] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 3]
                self.shardMatrix[idx][4] = self.train_array[i*numOfKeysPerInterval+((j+1)*keysPerShard)-1, 3]
            j= j+1
            idx = idx+1
            # Handle boundary case as lasty shard may have additional keys.  
            self.shardMatrix[idx][0] = idx+1
            self.shardMatrix[idx][1] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 2]
            self.shardMatrix[idx][2] = self.train_array[((i+1)*numOfKeysPerInterval)-1  , 2]
            self.shardMatrix[idx][3] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 3]
            self.shardMatrix[idx][4] = self.train_array[((i+1)*numOfKeysPerInterval)-1  , 3]
            
        #Last Interval may have less nu of keys
        nuOfShardsinLastInterval =  self.nuOfShards #self.keysInLastInterval // keysPerShard
        i = i+1
        for j in range(nuOfShardsinLastInterval-1):
            idx = i*self.nuOfShards+j
      
            self.shardMatrix[idx][0] = idx+1
            self.shardMatrix[idx][1] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 2]
            self.shardMatrix[idx][2] = self.train_array[i*numOfKeysPerInterval+((j+1)*keysPerShard)-1, 2]
            self.shardMatrix[idx][3] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 3]
            self.shardMatrix[idx][4] = self.train_array[i*numOfKeysPerInterval+((j+1)*keysPerShard)-1, 3]
        j= j+1
        idx = idx+1
        # Handle boundary case as lasty shard may have additional keys.  
        self.shardMatrix[idx][0] = idx+1
        self.shardMatrix[idx][1] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 2]
        self.shardMatrix[idx][2] = self.train_array[self.nuOfKeys-1  , 2]
        self.shardMatrix[idx][3] = self.train_array[i*numOfKeysPerInterval + j*keysPerShard, 3]
        self.shardMatrix[idx][4] = self.train_array[self.nuOfKeys -1 , 3]

    '''
        Learn shard boundaries per mapping interval. Initalize data structures
        to divide sorted mapped values in equal sized intervals, and learn 
        SP function for each interval. 
        
        Attribues
        ----------
        self.mappedIntervalMatrix : np array
           Data structure with mapped values at boundaries of 
           mapped intervals.
        self.shardMatrix : np array
           Data structure with mapped values at boundaries of 
           shard intervals.
        alpha : np array 
            Least square solution cofficients
        betas : np array 
            Array containing termination point for line segments
        
    '''
    def createShards(self):
        self.alphas_list = []
        self.betas_list = []
        self.createMappedIntervalMatrix()
        self.createShardMappingMatrix()
        
        for i in range(self.nuOfIntervals):
            x = self.train_array[i*self.numOfKeysPerInterval: ((i+1)*self.numOfKeysPerInterval), 3]
            y = np.arange(x.shape[0])
            #print('Interval %d' %(i))
            alphas, betas = self.trainShardingLinearFunctions(x, y,self.nuOfShards)
            self.alphas_list.append(alphas)
            self.betas_list.append(betas)
            
    '''
        Search in the grid cell for a particular key value. 
        
        Parameters
        ----------
       query  : Tuple
            Query point to be searched with 2 dimensional key value. 
            
        
        Returns
        -------
        CellIdx = Interger 
            Cell Index  corresponding to query point. 
        
    '''
    def searchCellGrid(self, query):
        
        found = False
        cellIdx = -1
        for i in range(self.cellSize):
             for j in range(self.cellSize):
                 if(query[0] >= self.cellMatrix[i+j*self.cellSize][0] and query[0] <= self.cellMatrix[i+j*self.cellSize][2]) and \
                     (query[1] >= self.cellMatrix[i+j*self.cellSize][1] and query[1] <= self.cellMatrix[i+j*self.cellSize][3]):
                         found = True
                         cellIdx = i+j*self.cellSize
                         break
             if (found == True):
                 break
        return cellIdx

    '''
        Do BST search for mapped interval based on query point mapped value
        
        Parameters
        ----------
       x  : float
            Query point mapped value. 
            
        
        Returns
        -------
       Index of mapped interval. 
        
    '''
    def search_mapped_interval(self, x):
        low = 0
        high = self.nuOfIntervals - 1
        mid = 0
        #print('searching for %f' %(x))
        while low <= high:

            mid = (high + low) // 2
            #print('mid is %d' %(mid))
            # If x is greater, ignore left half
            if self.mappedIntervalMatrix[mid][4] < x:
                low = mid + 1

            # If x is smaller, ignore right half
            elif self.mappedIntervalMatrix[mid][3] > x:
                high = mid - 1

            # means x is present at mid
            else:
                #print('\n returning page %d' %(mid))
                return mid        
        # If we reach here, then the element was not present
        #print('\n returning page %d' %(-1))    
        return -1
    
    '''
       Search for the shard interval based on mapped value. 
        
        Parameters
        ----------
        x  : float
            Query point mapped value. 
        
        intervalId : Integer
            Mapped interval to which query point belongs
            
        
        Returns
        -------
        Shard Id : Interger
            
    '''
    def search_shard_matrix(self, x, intervalId):
        shardOffset =  intervalId*self.nuOfShards      
        for i in range(self.nuOfShards):
            if ((x >= self.shardMatrix[shardOffset+i][3])
                and (x <= self.shardMatrix[shardOffset+i][4])):
                return i
        return -1 
    
    '''
       Idenitfy the mapped interval to which query point mapped value belongs 
        
        Parameters
        ----------
        x  : float
            Query point mapped value. 
        
             
        Returns
        -------
        Mapped Interval Id : Interger
            
    '''
    def sequentially_scan_mapped_interval(self, x):
        for i in range(self.nuOfIntervals):
            if (x <= self.mappedIntervalMatrix[i][4]):
                return i
        return -1 
    
    
    '''
       Search for the query point in the shard interval.  
        
        Parameters
        ----------
        query  : tuple
            Query point 2 dimensional key value.  
        
        intervalId : Integer
            Mapped interval to which query point belongs
        
             
        Returns
        -------
        Value corresponding to query point key
            
    '''
    def scan_shard(self, interval_id,shardId, query):
        
        mapped_interval_offset = interval_id*self.numOfKeysPerInterval
        shard_offset = mapped_interval_offset + shardId*self.keysPerShard
        end_offset = shard_offset+self.keysPerShard
        if(shardId == self.nuOfShards -1):
            if (interval_id != (self.nuOfIntervals-1)):
                end_offset = end_offset+ (self.numOfKeysPerInterval % self.keysPerShard)
            else:
                end_offset = self.nuOfKeys
            #print('Incrementing end offset by %d for shardId %d'%((self.numOfKeysPerInterval % self.keysPerShard),shardId))
        for i in range(shard_offset, end_offset):
            if (self.train_array[i,0] == query[0]) and (self.train_array[i,1]== query[1]):
                return self.train_array[i,2]
       
        if not ((interval_id == (self.nuOfIntervals-1)) and (shardId ==(self.nuOfShards -1))):
            # Search in adjacent shard
            for i in range (self.nuOfKeysToSearchinAdjacentShard):
                 if (self.train_array[i+end_offset,0] == query[0]) and (self.train_array[i+end_offset,1]== query[1]):
                    return self.train_array[i+end_offset,2]
        if not ((interval_id == 0) and (shardId ==0)):
            # Search in adjacent shard
            for i in range (self.nuOfKeysToSearchinAdjacentShard):
                 if (self.train_array[shard_offset-i,0] == query[0]) and (self.train_array[shard_offset-i,1]== query[1]):
                     return self.train_array[shard_offset-i,2]
        if self.debugPrint:        
            print('query point %d %d not found in shard Id %d interval_id = %d sharrd_offset %d %d' %(query[0], query[1], shardId,interval_id, shard_offset, end_offset))    
            print('Shard Id %d start %d %d end point %d %d '%(shardId, self.train_array[shard_offset,0],self.train_array[shard_offset,1], self.train_array[end_offset-1,0],self.train_array[end_offset-1,1],))
            
        return -1
    
    
    '''
       Search for the query point in the shard interval.  
        
        Parameters
        ----------
        query  : tuple
            Query point 2 dimensional key value.  
        
        intervalId : Integer
            Mapped interval to which query point belongs
        
             
        Returns
        -------
        Value corresponding to query point key
            
    '''
    def predict(self, query):
       
        cell_id = self.searchCellGrid(query)
        if (cell_id == -1):
            print('Query point %d %d not found' %(query[0],query[1]))
            return -1
        else:
            keyArea = np.abs((query[1] - self.cellMatrix[cell_id][1])*
                       (query[0] - self.cellMatrix[cell_id][0]))
     
            mapped_value =   self.cellMatrix[cell_id][7] + ((keyArea/self.cellMatrix[cell_id][8])*self.keysPerCell)
            intervalId =   self.search_mapped_interval(mapped_value)
            if(intervalId == -1):
                intervalId = self.sequentially_scan_mapped_interval(mapped_value)
                if(intervalId == -1):
                    print('Query point %d %d mapping value %f not found in sequential search' %(query[0],query[1], mapped_value))
                    return -1
                            
            v_pred = self.predictShardId(mapped_value, self.alphas_list[intervalId], self.betas_list[intervalId]).astype(int)
            #gtShardId = self.search_shard_matrix(mapped_value, intervalId)
            predShardId = v_pred[0]//self.keysPerShard
            if(predShardId < 0):
                predShardId= 0
            if(predShardId >= self.nuOfShards):
                predShardId = self.nuOfShards-1
                
             
            y_pred = self.scan_shard(intervalId,predShardId, query)
            if(y_pred == -1):
                if self.debugPrint:
                    print('query point %d %d not found with mapped value %f predicted shard id %d' 
                        %(query[0], query[1], mapped_value,predShardId ))    
                return 0
            return y_pred    
    
    
       
    '''
       Decompose range query into a union of smaller query rectangles each 
       belong to one and only one cell. 
        
        Parameters
        ----------
        query_l : tuple
            Range Query lower coordinate
        
        query_u  : tuple
            Range Query upper coordinate
                     
        Returns
        -------
        cell_list :  union of smaller query rectangles each 
       belong to one and only one cell.
            
    '''
    def range_query(self,query_l, query_u):
        lowerBound = False
        cell_list = []
        for i in range(self.cellSize):
            for j in range(self.cellSize):
                idx = j*self.cellSize+i
                if(query_l[0] >= self.cellMatrix[idx][0] and query_l[0] <= self.cellMatrix[idx][2]) and \
                     (query_l[1] >= self.cellMatrix[idx][1] and query_l[1] <= self.cellMatrix[idx][3]):
                    cell_list.append(idx)
                    lowerBound = True
                    break
            if(lowerBound == True):
                break
                
        if(lowerBound == False):
            if(self.debugPrint):
                print('Query Rectangle Outside the range')
            return cell_list
        else:
            if(self.debugPrint):
                print('lowerbound is a equal to %d'%(idx))
            x_offset = idx% self.cellSize
            j = j+1
            if(j == self.cellSize):
                j = 0
                i = i+1
            idx = j*self.cellSize+i
            while(i < self.cellSize):
                if ((idx%self.cellSize) < x_offset):
                    j = j+1
                    if(j == self.cellSize):
                        j = 0
                        i = i+1
                    idx = j*self.cellSize+i
                    continue
              
                if(query_u[0] >= self.cellMatrix[idx][0] and query_u[1] >= self.cellMatrix[idx][1]):
                #or (query_u[1] <= lisa.cellMatrix[i][3] and query_u[0] >= lisa.cellMatrix[i][0]):
                    cell_list.append(idx)
                j = j+1   
                if(j == self.cellSize):
                    j = 0
                    i = i+1
                idx = j*self.cellSize+i
        if self.debugPrint:
            print(cell_list)

        return cell_list
    
    '''
      Return keys belonging to range query from cells belonging to cell list
       Parameters
        ----------
        query_l : tuple
            Range Query lower coordinate
        
        query_u  : tuple
            Range Query upper coordinate
            
        cellList : List
            List contaning cells ids which are identified as part of 
        query
                     
        Returns
        -------
        keylist :  npArray
            Array of key/value pairs fetched by range query
               
                           
    '''
    
    def getKeysInRangeQuerySlow(self, cellList, query_l, query_u):
        keyList = []
        for i in cellList:
            nuOfKeys = self.keysPerCell
            startOffset = int(self.cellMatrix[i][6]*(self.keysPerCell))
            if i == ((self.cellSize*self.cellSize)-1):
                nuOfKeys = nuOfKeys + self.additionalKeysInLastCell 
            for j in range(startOffset, startOffset+nuOfKeys):
                 if(self.train_array[j, 0] >= query_l[0] and self.train_array[j, 0] <= query_u[0] )and \
                         (self.train_array[j, 1] >= query_l[1] and self.train_array[j, 1] <= query_u[1] ):
                        keyList.append(self.train_array[j, 0:3])
     
        return np.array(keyList)
    
    def predict_first_shard_range_query(self,query_l,query_u,cell_id,keyList):
       
        
        keyArea = np.abs((query_l[1] - self.cellMatrix[cell_id][1])*
                   (query_l[0] - self.cellMatrix[cell_id][0]))
    
        mapped_value =   self.cellMatrix[cell_id][7] + ((keyArea/self.cellMatrix[cell_id][8])*self.keysPerCell)
        intervalId =   self.search_mapped_interval(mapped_value)
        if(intervalId == -1):
            intervalId = self.sequentially_scan_mapped_interval(mapped_value)
            if(intervalId == -1):
                return keyList
    
        v_pred = self.predictShardId(mapped_value, self.alphas_list[intervalId], self.betas_list[intervalId]).astype(int)
        predShardId = v_pred[0]//self.keysPerShard
        if(predShardId < 0):
            predShardId= 0
        if(predShardId >= self.nuOfShards):
            predShardId = self.nuOfShards-1
        
        mapped_interval_offset = intervalId*self.numOfKeysPerInterval
        end_offset = mapped_interval_offset+self.numOfKeysPerInterval
        if (predShardId>0):
            predShardId = predShardId-1
        shard_offset = mapped_interval_offset + predShardId*self.keysPerShard
        for j in range(shard_offset, end_offset):
            if(self.train_array[j, 0] >= query_l[0] and self.train_array[j, 0] <= query_u[0] )and \
                (self.train_array[j, 1] >= query_l[1] and self.train_array[j, 1] <= query_u[1] ):
                keyList.append(self.train_array[j, 0:3])
        return keyList
    
    
    def predict_last_shard_range_query(self,query_l,query_u,cell_id,keyList):
       
    
        keyArea = np.abs((query_u[1] - self.cellMatrix[cell_id][1])*
                   (query_u[0] - self.cellMatrix[cell_id][0]))
    
        mapped_value =   self.cellMatrix[cell_id][7] + ((keyArea/self.cellMatrix[cell_id][8])*self.keysPerCell)
        intervalId =   self.search_mapped_interval(mapped_value)
        if(intervalId == -1):
            intervalId = self.sequentially_scan_mapped_interval(mapped_value)
            if(intervalId == -1):
                return keyList
    
        v_pred = self.predictShardId(mapped_value, self.alphas_list[intervalId], self.betas_list[intervalId]).astype(int)
        predShardId = v_pred[0]//self.keysPerShard
        if(predShardId < 0):
            predShardId= 0
        if(predShardId >= self.nuOfShards):
            predShardId = self.nuOfShards-1
        
        mapped_interval_offset = intervalId*self.numOfKeysPerInterval
        if (predShardId<(self.nuOfShards -1)):
           predShardId = predShardId+1
        start_offset = mapped_interval_offset
        shard_offset = mapped_interval_offset + predShardId*self.keysPerShard
        end_offset = shard_offset+self.keysPerShard
        if(predShardId == self.nuOfShards -1):
            if (intervalId != (self.nuOfIntervals-1)):
                end_offset = end_offset+ (self.numOfKeysPerInterval % self.keysPerShard)
            else:
                end_offset = self.nuOfKeys
       
        for j in range(start_offset, end_offset):
            if(self.train_array[j, 0] >= query_l[0] and self.train_array[j, 0] <= query_u[0] )and \
                (self.train_array[j, 1] >= query_l[1] and self.train_array[j, 1] <= query_u[1] ):
                keyList.append(self.train_array[j, 0:3])
               
       
        return keyList


        
    def getKeysInRangeQuery(self,cellList, query_l, query_u):
        keyList = []
        cellId = cellList[0]
        keyList = self.predict_first_shard_range_query(query_l, query_u, cellId,keyList)
        cellList.pop(0)
        if len(cellList) == 0:
            return np.array(keyList)
        cellId = cellList[-1]
        cellList.pop(-1)
        for i in cellList:
            nuOfKeys = self.keysPerCell
            startOffset = int(self.cellMatrix[i][6]*(self.keysPerCell))
            if i == ((self.cellSize*self.cellSize)-1):
                nuOfKeys = nuOfKeys + self.additionalKeysInLastCell 
            for j in range(startOffset, startOffset+nuOfKeys):
                 #if(lisa.train_array[j, 0] >= query_l[0] and lisa.train_array[j, 0] <= query_u[0] )and \
                 #        (lisa.train_array[j, 1] >= query_l[1] and lisa.train_array[j, 1] <= query_u[1] ):
                keyList.append(self.train_array[j, 0:3])
       
        keyList = self.predict_last_shard_range_query(query_l,query_u, cellId, keyList)
        return np.array(keyList)

    '''
       Calculate euclidean distance between arguments left and right
                
    '''
    def distance(self, left, right):
        """ Returns the square of the distance between left and right. """
        return np.sqrt(((left[0] - right[0]) ** 2) + ((left[1] - right[1]) ** 2))
        
    '''
      Return keys/value pairs belonging to knn of query point
       Parameters
        ----------
        queryPoint : tuple
            Query point 2 dimensional key coordinate
        
                  
        k : Integer
            Number of neighbours to return. 
        
                     
        Returns
        -------
        keylist :  npArray
           key value pairs belonging to knn of query point
               
                           
    '''
    def findKnnNeighbours (self, queryPoint, k):
        for scale in range (1,5):
            delta = self.initDelta**scale
            query_l = (queryPoint[0]-delta, queryPoint[1]-delta)
            query_h = (queryPoint[0]+delta, queryPoint[1]+delta)
            if (query_l < (self.train_array[0,0], self.train_array[0,1])):
                query_l = (self.train_array[0,0], self.train_array[0,1])
            if (query_h  > (self.train_array[-1,0], self.train_array[-1,1])):
                query_h = (self.train_array[-1,0], self.train_array[-1,1])
                
            cellList =self.range_query(query_l,query_h)
            if(len(cellList) == 0):
                print('range query is empty')
                return None
            neighboursKeySet = self.getKeysInRangeQuery(cellList,query_l,query_h )
            if (len(neighboursKeySet) < k):
                if self.debugPrint:
                    print('No of keys found = %d' %(len(neighboursKeySet) ))
                continue   
            neighboursKeySet = np.hstack((neighboursKeySet, np.zeros((neighboursKeySet.shape[0], 1),dtype=neighboursKeySet.dtype)))
            idx = np.where((neighboursKeySet[:, 0] == queryPoint[0] ) & (neighboursKeySet[:, 1] == queryPoint[1]))
            neighboursKeySet[:, 3] = self.distance(queryPoint,(neighboursKeySet[:, 0], neighboursKeySet[:,1]))
            #neighboursKeySet[:, 3] = np.sqrt(((neighboursKeySet[:, 2]- neighboursKeySet[idx, 2]) ** 2))
                                             
            neighboursKeySet = neighboursKeySet[neighboursKeySet[:,3].argsort()]
           
            return neighboursKeySet[0:k, 3]
        return (None, None)
    
    '''
     Predict range query for lisa model
                                
    '''
    def predict_range_query(self, query_l, query_u):
        cellList =self.range_query(query_l, query_u)    
        if(len(cellList) == 0):
            if self.debugPrint:
                print('range query is empty')
            return -1
        else:
            neighboursKeySet = self.getKeysInRangeQuery(cellList, query_l, query_u)
            return np.sort(neighboursKeySet[:, -1])
        
    '''
     Predict knn query for lisa model
                                
    '''
    def predict_knn_query(self, query, k):
          y_pred = self.findKnnNeighbours(query, k)
          return np.sort(y_pred)
          
        
            
            

    '''
       Train the lisa model: Training consists of:
            a) cell grid generation
            b) Applying mapping function to keys values taking into account '
               cell boundaries
            c) Learning Shard boundaries using piecewise linear functions. 
    
       Parameters
        ----------
        Train and test point np arrays
       
        Returns
        -------
        mse: Float
           Mean square error for eval points
           time : Time taken to build the lisaBaseline model. 
        
    '''  
    def train(self, x_train, y_train, x_test, y_test):

        print(x_train.shape)
        print(x_test.shape)
        print(y_train.shape)
        print(y_test.shape)
    
        
        np.set_printoptions(threshold=100000)
        start_time = timer()
        self.train_array = np.hstack((x_train, y_train.reshape(-1, 1),
                                      np.zeros((x_train.shape[0], 1),
                                               dtype=x_train.dtype)))
        #print( self.train_array[0:100,:])
        self.train_array = self.train_array.astype('float64')
        if (self.generate_grid_cells() == -1):
            print('Invalid Configuration')
            return -1, timer() - start_time
        self.compute_mapping_value()
        self.createShards()
        end_time = timer()
        print('/n build time %f' % (end_time - start_time))
        #print(self.train_array)
        test_data_size = x_test.shape[0]
        pred_y = []
        #for i in range(20):
        print('\n In Lisabaseline.build evaluation %d data points' %
              (test_data_size))
        error_count = 0
        for i in range(test_data_size):
            y_hat = self.predict(x_test[i])
            if(y_hat != y_test[i]):
                print(' pred = %d, gt = %d' %(y_hat, y_test[i] ))
                error_count = error_count+1
            pred_y.append(y_hat)

        pred_y = np.array(pred_y)
        #mse = metrics.mean_absolute_error(y_test, pred_y)
        mse = metrics.mean_squared_error(y_test, pred_y)
        print('error count is %d, test size is %d ratio is %f' %(error_count,test_data_size, error_count/test_data_size ))
        print('nuOfIntervals =%d, numOfKeysPerInterval = %d nuOfShards = %d keysperShard = %d NuofKeys = %d keysInLastInterval = %d'
                      %(self.nuOfIntervals, self.numOfKeysPerInterval,self.nuOfShards,self.keysPerShard, self.nuOfKeys, self.keysInLastInterval) )

        print('cellSize = %d, keysPerCell = %d, nuOfKeys = %d additionalKeysInLastCell = %d' %(self.cellSize, self.keysPerCell,  self.nuOfKeys, self.additionalKeysInLastCell ))
        if self.debugPrint:
            print(self.cellMatrix)
        return mse, end_time - start_time
     
        
        